from confluent_kafka import Consumer
from kubernetes import client, config
import json
import logging
import os
from scanner_config import SCANNER_CONFIGS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_preprocessing_job(scanner_type, scanner_name, repo_name, org_id):
    """Create a preprocessing job for completed scanner results."""
    job_name = f"preprocess-{scanner_type}-{scanner_name}-{repo_name}"
    
    preprocessing_job = client.V1Job(
        metadata=client.V1ObjectMeta(
            name=job_name,
            labels={
                'job-type': 'preprocessing',
                'scanner-type': scanner_type,
                'scanner-name': scanner_name,
                'repo-name': repo_name
            }
        ),
        spec=client.V1JobSpec(
            template=client.V1PodTemplateSpec(
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="preprocessing",
                            image="python:3.12-slim",
                            command=["/bin/sh", "-c"],
                            args=[
                                "pip install -r /data/scripts/requirements.txt && "
                                "python3 /data/scripts/store_data.py"
                            ],
                            env=[
                                client.V1EnvVar(name="REPO_NAME", value=repo_name),
                                client.V1EnvVar(name="ORG_ID", value=org_id),
                                client.V1EnvVar(name="SCANNER_TYPE", value=scanner_type),
                                client.V1EnvVar(name="SCANNER_NAME", value=scanner_name)
                            ],
                            volume_mounts=[
                                client.V1VolumeMount(
                                    name="repo-storage",
                                    mount_path="/data/repos"
                                ),
                                client.V1VolumeMount(
                                    name="script-storage",
                                    mount_path="/data/scripts"
                                )
                            ]
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name="script-storage",
                            config_map=client.V1ConfigMapVolumeSource(
                                name="preprocess-scripts"
                            )
                        ),
                        client.V1Volume(
                            name="repo-storage",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                claim_name="repo-storage-pvc"
                            )
                        )
                    ],
                    restart_policy="Never"
                )
            ),
            ttl_seconds_after_finished=3600
        )
    )
    
    return preprocessing_job

def create_scanner_jobs(scanner_type, repo_name, org_id):
    """Create jobs for all scanners of the specified type."""
    try:
        config.load_incluster_config()
        batch_v1 = client.BatchV1Api()
        
        # Clean up any existing jobs for this repo and scanner type
        try:
            jobs = batch_v1.list_namespaced_job(
                namespace="default",
                label_selector=f"repo-name={repo_name},scanner-type={scanner_type}"
            )
            for job in jobs.items:
                batch_v1.delete_namespaced_job(
                    name=job.metadata.name,
                    namespace="default",
                    body=client.V1DeleteOptions(propagation_policy='Background')
                )
        except Exception as e:
            logger.error(f"Error cleaning up old jobs: {e}")

        # Get all scanners for the specified type
        scanners = SCANNER_CONFIGS.get(scanner_type, {})
        if not scanners:
            logger.error(f"No scanners configured for type: {scanner_type}")
            return

        for scanner_name, scanner_config in scanners.items():
            job_name = f"{scanner_type}-{scanner_name}-{repo_name}-{org_id}"
            
            # Format paths for this specific scan
            source_path = f"/data/repos/{repo_name}"
            results_dir = f"/data/repos/results/{repo_name}"
            output_path = f"{results_dir}/{scanner_name}_result.json"
            
            # Create init container to prepare directories
            init_container = client.V1Container(
                name="init-dirs",
                image="busybox",
                command=["/bin/sh", "-c"],
                args=[f"mkdir -p {source_path} {results_dir}"],
                volume_mounts=[
                    client.V1VolumeMount(
                        name="repo-storage",
                        mount_path="/data/repos"
                    )
                ]
            )

            # Format command with actual paths
            command = [
                cmd.format(
                    source_path=source_path,
                    output_path=output_path,
                ) for cmd in scanner_config['command']
            ]

            scanner_container = client.V1Container(
                name=scanner_name,
                image=scanner_config['image'],
                command=command,
                volume_mounts=[
                    client.V1VolumeMount(
                        name="repo-storage",
                        mount_path="/data/repos"
                    )
                ]
            )

            job = client.V1Job(
                metadata=client.V1ObjectMeta(
                    name=job_name,
                    labels={
                        'scanner-type': scanner_type,
                        'scanner-name': scanner_name,
                        'repo-name': repo_name
                    }
                ),
                spec=client.V1JobSpec(
                    template=client.V1PodTemplateSpec(
                        spec=client.V1PodSpec(
                            init_containers=[init_container],
                            containers=[scanner_container],
                            volumes=[
                                client.V1Volume(
                                    name="repo-storage",
                                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                        claim_name="repo-storage-pvc"
                                    )
                                )
                            ],
                            restart_policy="Never"
                        )
                    ),
                    backoff_limit=1,
                    ttl_seconds_after_finished=3600,
                    # Add completion handler
                    completion_mode="NonIndexed",
                    completions=1
                )
            )
            
            try:
                batch_v1.create_namespaced_job(namespace="default", body=job)
                logger.info(f"Created {scanner_type}/{scanner_name} job: {job_name}")
                
                # Create preprocessing job
                preprocess_job = create_preprocessing_job(scanner_type, scanner_name, repo_name, org_id)
                batch_v1.create_namespaced_job(namespace="default", body=preprocess_job)
                logger.info(f"Created preprocessing job for {scanner_type}/{scanner_name}")
                
            except client.exceptions.ApiException as e:
                if e.status == 409:  # Conflict
                    logger.warning(f"Job {job_name} already exists, skipping")
                else:
                    raise
                    
    except Exception as e:
        logger.error(f"Error creating {scanner_type} jobs: {e}")



def main():
    consumer = Consumer({
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
        'group.id': 'scanner-consumer',
        'auto.offset.reset': 'earliest'
    })
    consumer.subscribe(['scanner.sast', 'scanner.secrets'])
    
    logger.info("Scanner consumer started, waiting for messages...")
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logger.error(f"Consumer error: {msg.error()}")
                continue
            try:
                # Properly decode and parse the message
                message_bytes = msg.value()
                if isinstance(message_bytes, bytes):
                    message_str = message_bytes.decode('utf-8')
                    scan_event = json.loads(message_str)
                else:
                    logger.error("Received message is not in bytes format")
                    continue

                scanner_type = msg.topic().split('.')[1]
                logger.info(f"Received {scanner_type} scan request for {scan_event['repo_name']}")
                
                create_scanner_jobs(
                    scanner_type=scanner_type,
                    repo_name=scan_event['repo_name'],
                    org_id=scan_event['org_id']
                )
                
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                
    except KeyboardInterrupt:
        logger.info("Shutting down consumer...")
    finally:
        consumer.close()
if __name__ == "__main__":
    main()
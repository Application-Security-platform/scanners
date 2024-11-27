from confluent_kafka import Consumer, Producer
from kubernetes import client, config, watch
import json
import logging
import os
from scanner_config import SCANNER_CONFIGS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_scanner_jobs(scanner_type, repo_name, org_id):
    """Create jobs for all scanners of the specified type."""
    try:
        config.load_incluster_config()
        batch_v1 = client.BatchV1Api()
        
        # Clean up existing jobs
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
            
            # Create job spec similar to before
            job = create_scanner_job_spec(
                job_name, scanner_name, scanner_config, 
                source_path, results_dir, output_path
            )
            
            try:
                # Create the job
                batch_v1.create_namespaced_job(namespace="default", body=job)
                logger.info(f"Created {scanner_type}/{scanner_name} job: {job_name}")
                
                # Watch for job completion
                watch_and_notify_completion(
                    batch_v1, job_name, scanner_type, 
                    scanner_name, repo_name, org_id
                )
                
            except client.exceptions.ApiException as e:
                if e.status == 409:
                    logger.warning(f"Job {job_name} already exists, skipping")
                else:
                    raise
                    
    except Exception as e:
        logger.error(f"Error creating {scanner_type} jobs: {e}")

def watch_and_notify_completion(batch_v1, job_name, scanner_type, scanner_name, repo_name, org_id):
    """Watch job completion and send Kafka message for preprocessing."""
    
    w = watch.Watch()
    
    def send_preprocess_message():
        producer = Producer({
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            'message.max.bytes': 1000000
        })
        
        preprocess_event = {
            'scanner_type': scanner_type,
            'scanner_name': scanner_name,
            'repo_name': repo_name,
            'org_id': org_id,
            'job_name': job_name
        }
        
        try:
            producer.produce(
                'preprocessing.trigger',
                value=json.dumps(preprocess_event).encode('utf-8')
            )
            producer.flush()
            logger.info(f"Sent preprocessing trigger for {job_name}")
        except Exception as e:
            logger.error(f"Failed to send preprocessing message: {e}")
        finally:
            producer.close()

    try:
        for event in w.stream(
            batch_v1.list_namespaced_job,
            namespace="default",
            timeout_seconds=3600
        ):
            job = event['object']
            if job.metadata.name == job_name and job.status.succeeded:
                send_preprocess_message()
                w.stop()
                break
    except Exception as e:
        logger.error(f"Error watching job {job_name}: {e}")

def main():
    # Main consumer code remains the same
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
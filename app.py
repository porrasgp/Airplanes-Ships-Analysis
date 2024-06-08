import os
import boto3
import numpy as np
import numba
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score

# Load environment variables (only needed if running locally with a .env file)
if not os.getenv("GITHUB_ACTIONS"):
    from dotenv import load_dotenv
    load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
BUCKET_NAME = "computervisionairplaneandships"
PREFIXES = ["airplanes/planesnet/planesnet", "Ships/shipsnet/shipsnet"]

# Your existing code here


def process_image_data_parallel_optimized(images_data):
    results = np.zeros(len(images_data), dtype=np.float64)
    for i in numba.prange(len(images_data)):
        # Vectorize the loop
        results[i] = np.sum(images_data[i]) 
    return results

if __name__ == "__main__":
    s3 = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)

    all_results = []
    all_labels = []

    max_sequence_length = 1000  # Adjust as per your needs

    for prefix in PREFIXES:
        objects = s3.list_objects(Bucket=BUCKET_NAME, Prefix=f"{prefix}/")["Contents"]

        for obj in objects:
            key = obj["Key"]
            image_object = s3.get_object(Bucket=BUCKET_NAME, Key=key)
            image_data = np.frombuffer(image_object['Body'].read(), dtype=np.uint8)

            # Call the optimized parallel function
            result = process_image_data_parallel_optimized(image_data)

            # Error handling to avoid padding error
            if len(result) > max_sequence_length:
                result = result[:max_sequence_length]
            else:
                # Pad with zeros if the sequence is shorter
                result = np.pad(result, (0, max_sequence_length - len(result)), 'constant')

            # Check sequence length after trimming and padding
            print(f"Result length for image {key} after adjustment: {len(result)}")

            all_results.append(result)
            # Add label based on your dataset structure
            # For now, label 0 is for airplanes and 1 is for ships
            all_labels.append(0 if "airplanes" in prefix else 1)

    # Convert lists to NumPy arrays
    X = np.array(all_results)
    y = np.array(all_labels)

    # Split the dataset into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Create an SVM classifier
    clf = SVC(kernel='linear', C=1.0)

    # Train the classifier
    clf.fit(X_train, y_train)

    # Make predictions on the test set
    y_pred = clf.predict(X_test)

    # Calculate accuracy
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Classifier accuracy: {accuracy * 100:.2f}%")

    # Write metrics to file
    with open('metrics.txt', 'w') as outfile:
        outfile.write(F'\nModel Results = {accuracy * 100:.2f}%')
    

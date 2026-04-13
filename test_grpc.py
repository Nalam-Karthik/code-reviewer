# test_grpc.py — run this on your Mac to test gRPC
import grpc
import sys
sys.path.insert(0, "flask-api")
from proto import review_pb2, review_pb2_grpc

def main():
    # Connect to gRPC server
    channel = grpc.insecure_channel("localhost:50051")
    stub    = review_pb2_grpc.CodeReviewServiceStub(channel)

    # Build a batch request with 3 files
    request = review_pb2.BatchReviewRequest(
        user_id="1",
        files=[
            review_pb2.CodeFile(
                filename="auth.py",
                language="python",
                code='def login(u,p):\n    query="SELECT * FROM users WHERE user=\'"+u+"\'"\n    return db.execute(query)'
            ),
            review_pb2.CodeFile(
                filename="utils.py",
                language="python",
                code="def add(a, b):\n    return a + b"
            ),
            review_pb2.CodeFile(
                filename="app.js",
                language="javascript",
                code="const getData = async () => {\n    const res = await fetch('/api/data')\n    return res.json()\n}"
            ),
        ]
    )

    print("Sending batch review request...\n")

    # Results stream back one at a time as they're ready
    for response in stub.BatchReview(request):
        print(f"File: {response.filename}")
        print(f"Score: {response.score}/100")
        print(f"Summary: {response.summary}")
        print(f"Success: {response.success}")
        print("---")

if __name__ == "__main__":
    main()

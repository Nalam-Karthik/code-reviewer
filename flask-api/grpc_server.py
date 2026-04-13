# flask-api/grpc_server.py
#
# gRPC server — runs alongside Flask but on port 50051.
# Used by CI/CD tools to review multiple files in one call.
#
# REST vs gRPC — why gRPC here:
# - REST: one HTTP request per file, overhead per request
# - gRPC: one connection, stream multiple results back efficiently
# - gRPC uses binary Protocol Buffers (faster than JSON)
# - gRPC is typed — the .proto file IS the contract
#
# Run this separately: python grpc_server.py

import grpc
import time
import logging
from concurrent import futures

# These are auto-generated from review.proto
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from proto import review_pb2, review_pb2_grpc
from app import create_app
from app.services.ai import get_code_review

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# We need Flask app context to use SQLAlchemy etc.
flask_app = create_app()


class CodeReviewServicer(review_pb2_grpc.CodeReviewServiceServicer):
    """
    Implements the gRPC service defined in review.proto.
    One method per RPC defined in the proto file.
    """

    def BatchReview(self, request, context):
        """
        Receive a batch of files, review each one, stream results back.

        'yield' here is what makes this a streaming RPC —
        results come back one at a time as they're ready,
        instead of waiting for ALL files to finish.
        """
        logger.info(
            f"BatchReview called: {len(request.files)} files "
            f"from user_id={request.user_id}"
        )

        with flask_app.app_context():
            for file in request.files:
                logger.info(f"Reviewing: {file.filename} ({file.language})")

                result = get_code_review(
                    language=file.language,
                    code=file.code,
                    past_reviews=[]   # no memory for batch (Day 3 enhancement)
                )

                if result["error"] and not result["review"]:
                    # Stream an error response for this file
                    yield review_pb2.ReviewResponse(
                        filename = file.filename,
                        language = file.language,
                        success  = False,
                        error    = result["error"]
                    )
                else:
                    review = result["review"]
                    yield review_pb2.ReviewResponse(
                        filename = file.filename,
                        language = file.language,
                        summary  = review.get("summary", ""),
                        score    = review.get("score") or 0,
                        success  = True,
                        error    = ""
                    )

                # Small delay so client can process each streamed response
                time.sleep(0.1)


def serve():
    """Start the gRPC server on port 50051."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))

    review_pb2_grpc.add_CodeReviewServiceServicer_to_server(
        CodeReviewServicer(), server
    )

    port = "50051"
    server.add_insecure_port(f"[::]:{port}")
    server.start()

    logger.info(f"gRPC server running on port {port}")
    logger.info("Waiting for batch review requests...")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    serve()
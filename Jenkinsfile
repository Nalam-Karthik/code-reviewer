// Jenkinsfile
// Place this at the project root — Jenkins finds it automatically.
//
// Pipeline stages:
//   1. Checkout  — clone the repo
//   2. Lint      — check code style with flake8
//   3. Test      — run pytest suite
//   4. Build     — build Docker image
//   5. Deploy    — restart flask-api container with new image
//
// If ANY stage fails, all subsequent stages are skipped.
// This means bad code never gets deployed.

pipeline {

    // Run on any available Jenkins agent
    agent any

    // Environment variables available to all stages
    environment {
        IMAGE_NAME = "code-reviewer-api"
        IMAGE_TAG  = "${BUILD_NUMBER}"   // Jenkins build number as tag e.g. "42"
    }

    stages {

        // ── Stage 1: Checkout ──────────────────────────────
        stage('Checkout') {
            steps {
                // Jenkins clones your GitHub repo here automatically
                // No explicit step needed — checkout scm handles it
                checkout scm
                echo "Checked out branch: ${env.BRANCH_NAME}"
            }
        }

        // ── Stage 2: Lint ──────────────────────────────────
        stage('Lint') {
            steps {
                dir('flask-api') {
                    sh '''
                        pip3 install flake8 --quiet
                        # E501 = line too long (we skip it, not critical)
                        # W503 = line break before binary operator (style preference)
                        flake8 app/ --max-line-length=120 --ignore=E501,W503 --statistics
                    '''
                }
            }
        }

        // ── Stage 3: Test ──────────────────────────────────
        stage('Test') {
            steps {
                dir('flask-api') {
                    sh '''
                        pip3 install -r requirements.txt --quiet
                        # Run pytest — if any test fails, this stage fails
                        # and Deploy never runs
                        pytest tests/ -v --tb=short
                    '''
                }
            }
            post {
                always {
                    // Archive test results so you can see them in Jenkins UI
                    junit allowEmptyResults: true, testResults: 'flask-api/test-results/*.xml'
                }
            }
        }

        // ── Stage 4: Build Docker Image ────────────────────
        stage('Build') {
            steps {
                dir('flask-api') {
                    sh '''
                        docker build \
                            -t ${IMAGE_NAME}:${IMAGE_TAG} \
                            -t ${IMAGE_NAME}:latest \
                            .
                        echo "Built image: ${IMAGE_NAME}:${IMAGE_TAG}"
                    '''
                }
            }
        }

        // ── Stage 5: Deploy ────────────────────────────────
        stage('Deploy') {
            // Only deploy from main branch — not feature branches
            when {
                branch 'main'
            }
            steps {
                sh '''
                    # Restart only flask-api with the new image
                    # --no-deps means don't restart MySQL/Redis etc.
                    docker compose up -d --no-deps --build flask-api
                    echo "Deployed ${IMAGE_NAME}:${IMAGE_TAG}"
                '''
            }
        }
    }

    // ── Post-pipeline notifications ────────────────────────
    post {
        success {
            echo "Pipeline passed. ${IMAGE_NAME}:${IMAGE_TAG} is live."
        }
        failure {
            echo "Pipeline FAILED at stage. Check logs above."
        }
        always {
            // Clean up dangling Docker images after every build
            sh 'docker image prune -f || true'
        }
    }
}
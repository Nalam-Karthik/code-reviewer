pipeline {

    agent any

    environment {
        IMAGE_NAME = "code-reviewer-api"
        IMAGE_TAG  = "${BUILD_NUMBER}"
    }

    stages {

        // ── Stage 1: Checkout ──────────────────────────────
        stage('Checkout') {
            steps {
                checkout scm
                echo "Checked out commit: ${env.GIT_COMMIT}"
            }
        }

        // ── Stage 2: Lint ──────────────────────────────────
        stage('Lint') {
            steps {
                dir('flask-api') {
                    sh '''
                        pip3 install flake8 --quiet --break-system-packages
                        
                        # Fix PATH so Jenkins can find flake8
                        export PATH=$HOME/.local/bin:$PATH
                        
                        flake8 app/ \
                            --max-line-length=120 \
                            --ignore=E501,W503,E221,E241,E251,E231,E262,E272,E302,E303,E401,W291,W292,W293,W391,F841 \
                            --statistics
                    '''
                }
            }
        }

        // ── Stage 3: Test ──────────────────────────────────
        stage('Test') {
            steps {
                dir('flask-api') {
                    sh '''
                        pip3 install -r requirements.txt --quiet --break-system-packages
                        pip3 install pytest --quiet --break-system-packages
                        
                        # Ensure pytest is found
                        export PATH=$HOME/.local/bin:$PATH
                        
                        pytest tests/ -v --tb=short
                    '''
                }
            }
            post {
                always {
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
            steps {
                sh '''
                    docker compose up -d --no-deps --build flask-api
                    echo "Deployed ${IMAGE_NAME}:${IMAGE_TAG}"
                '''
            }
        }
    }

    post {
        success {
            echo "Pipeline passed. ${IMAGE_NAME}:${IMAGE_TAG} is live."
        }
        failure {
            echo "Pipeline FAILED at stage. Check logs above."
        }
        always {
            sh 'docker image prune -f || true'
        }
    }
}
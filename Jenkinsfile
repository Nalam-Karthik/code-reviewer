pipeline {

    agent any

    environment {
        IMAGE_NAME = "code-reviewer-api"
        IMAGE_TAG  = "${BUILD_NUMBER}"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                echo "Checked out commit: ${env.GIT_COMMIT}"
            }
        }

        stage('Lint') {
            steps {
                dir('flask-api') {
                    sh '''
                        python3 -m pip install --upgrade pip --break-system-packages
                        python3 -m pip install flake8 --break-system-packages

                        export PATH=$HOME/.local/bin:$PATH

                        flake8 app/ \
                            --max-line-length=120 \
                            --ignore=E501,W503,E221,E241,E251,E231,E262,E272,E302,E303,E401,W291,W292,W293,W391,F841 \
                            --statistics
                    '''
                }
            }
        }

        stage('Test') {
            steps {
                dir('flask-api') {
                    sh '''
                        # 🔥 CRITICAL FIX
                        python3 -m pip install --upgrade pip setuptools wheel --break-system-packages

                        # Install dependencies AFTER fixing setuptools
                        python3 -m pip install -r requirements.txt --break-system-packages

                        python3 -m pip install pytest --break-system-packages

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

        stage('Build') {
            steps {
                dir('flask-api') {
                    sh '''
                        # Fix docker permission properly
                        sudo chmod 666 /var/run/docker.sock || true

                        docker build \
                            -t ${IMAGE_NAME}:${IMAGE_TAG} \
                            -t ${IMAGE_NAME}:latest \
                            .
                    '''
                }
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    sudo chmod 666 /var/run/docker.sock || true

                    docker compose up -d --no-deps --build flask-api
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
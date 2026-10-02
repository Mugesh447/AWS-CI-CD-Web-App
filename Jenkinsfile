pipeline {
    agent any

    stages {
        stage('Install dependencies') {
            steps {
                sh 'python -m pip install -r app/requirements.txt'
            }
        }

        stage('Test') {
            steps {
                sh 'pytest -q'
            }
        }

        stage('Build image') {
            steps {
                sh 'docker build -t aws-cicd-webapp:${BUILD_NUMBER} .'
            }
        }
    }
}

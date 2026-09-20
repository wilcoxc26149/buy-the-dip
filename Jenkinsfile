pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  environment {
    USE_MOCK_DATA = '1'
    CI = '1'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Unit tests') {
      steps {
        script {
          if (isUnix()) {
            sh 'python3 -m venv .venv && .venv/bin/python -m pip install -U pip && .venv/bin/python -m pip install -r requirements-dev.txt && mkdir -p reports && .venv/bin/python -m pytest tests/unit --junitxml=reports/unit.xml'
          } else {
            bat 'python -m venv .venv && .venv\\Scripts\\python.exe -m pip install -U pip && .venv\\Scripts\\python.exe -m pip install -r requirements-dev.txt && if not exist reports mkdir reports && .venv\\Scripts\\python.exe -m pytest tests/unit --junitxml=reports/unit.xml'
          }
        }
      }
    }

    stage('Playwright') {
      steps {
        script {
          if (isUnix()) {
            sh '.venv/bin/python -m playwright install chromium && .venv/bin/python -m pytest tests/e2e --junitxml=reports/e2e.xml'
          } else {
            bat '.venv\\Scripts\\python.exe -m playwright install chromium && .venv\\Scripts\\python.exe -m pytest tests/e2e --junitxml=reports/e2e.xml'
          }
        }
      }
    }
  }

  post {
    always {
      junit allowEmptyResults: true, testResults: 'reports/*.xml'
      archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
    }
  }
}

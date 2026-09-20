pipeline {
  agent { label 'windows-host' }

  options {
    timestamps()
    disableConcurrentBuilds()
    skipDefaultCheckout()
  }

  environment {
    USE_MOCK_DATA = '1'
    CI = '1'
    LOCAL_REPO = 'C:/Users/wilco/projects/buy-the-dip'
  }

  stages {
    stage('Unit tests') {
      steps {
        dir(env.LOCAL_REPO) {
          bat '''
            if not exist "%WORKSPACE%/.venv/Scripts/python.exe" python -m venv "%WORKSPACE%/.venv"
            "%WORKSPACE%/.venv/Scripts/python.exe" -m pip install -U pip
            "%WORKSPACE%/.venv/Scripts/python.exe" -m pip install -r requirements-dev.txt
            if not exist reports mkdir reports
            "%WORKSPACE%/.venv/Scripts/python.exe" -m pytest tests/unit --junitxml=reports/unit.xml
          '''
        }
      }
    }

    stage('Playwright') {
      steps {
        dir(env.LOCAL_REPO) {
          bat '''
            "%WORKSPACE%/.venv/Scripts/python.exe" -m playwright install chromium
            "%WORKSPACE%/.venv/Scripts/python.exe" -m pytest tests/e2e --junitxml=reports/e2e.xml
          '''
        }
      }
    }
  }

  post {
    always {
      dir(env.LOCAL_REPO) {
        junit allowEmptyResults: true, testResults: 'reports/*.xml'
        archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
      }
    }
  }
}

# AWS CI/CD Web App


A small Flask web application packaged with Docker and prepared for CI/CD using Jenkins and GitHub Actions.

## Project structure

```text
aws-cicd-webapp/
├── app/
│   ├── app.py
│   ├── requirements.txt
│   └── templates/
│       └── index.html
├── tests/
│   └── test_app.py
├── Dockerfile
├── .dockerignore
├── .gitignore
├── docker-compose.yml
├── Jenkinsfile
├── README.md
└── .github/workflows/ci-cd.yml
```

## Run locally

```bash
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install -r app/requirements.txt
pytest -q
python app/app.py
```

Open `http://localhost:5001` and check `http://localhost:5001/health`.

The dashboard opens with a login screen. Create an account from the
authentication screen, then use that username and password to sign in. Set
`APP_USER`, `APP_PASSWORD`, and `FLASK_SECRET_KEY` environment variables before
deployment. `APP_PASSWORD` seeds the admin password when the database is first
created. If `app/data/app.db` already exists, change the account password from
Profile settings; changing the environment variable does not rewrite an
existing password hash. SQLite stores users and deployment records in that
database, and Docker Compose mounts the folder so data survives container
restarts.

Passwords are stored with Werkzeug's salted password hashing and are never
stored as plaintext. For HTTPS production deployments, set `COOKIE_SECURE=true`
so the session cookie is sent only over HTTPS.

## Runtime monitoring and security checks

The dashboard's **Live application monitoring** panel and authenticated
`/api/monitoring` endpoint report request count, average response time, and
uptime measured inside the current Flask worker. These in-memory counters reset
when that worker restarts; with multiple workers, they are per-worker values
and are not an aggregate or a substitute for CloudWatch metrics.

The **Runtime and security checks** panel and authenticated `/api/diagnostics`
endpoint check database connectivity, Flask debug mode, session signing-key
configuration, HTTPS-only session cookies, and use of the default seed
password. Warnings are actionable configuration reminders, not a penetration
test. Set a stable, non-default `FLASK_SECRET_KEY` of at least 32 characters,
replace the default `APP_PASSWORD`, and set `COOKIE_SECURE=true` when the app
is served over HTTPS.

AWS service health and billing values elsewhere in the dashboard are sample
dashboard data; this local application does not query ECS, ECR, or CloudWatch.

## Run with Docker

```bash
docker compose up --build
```

## AWS deployment

The GitHub Actions workflow runs tests on pull requests and, after a push to
`main`, builds the image, pushes it to Amazon ECR, and deploys it to an Amazon
ECS Fargate service.

Create the ECR repository, ECS cluster, ECS service, CloudWatch log group, and
an IAM OIDC deployment role first. Configure these GitHub repository values:

### Variables

```text
AWS_REGION       us-east-1
ECR_REPOSITORY   aws-cicd-webapp
ECS_CLUSTER      your-ecs-cluster
ECS_SERVICE      your-ecs-service
```

### Secrets

```text
AWS_DEPLOY_ROLE_ARN
ECS_EXECUTION_ROLE_ARN
```

The deployment role needs permission to push to ECR and update the ECS service.
The ECS execution role needs the standard `AmazonECSTaskExecutionRolePolicy`.
After these values are configured, push to `main` to trigger the deployment.

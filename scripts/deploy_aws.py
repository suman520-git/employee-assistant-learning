import os
from pathlib import Path
import re
import shlex
import time

import boto3


REGION = "ap-south-1"
INSTANCE_ID = "i-0c788632c7574d1a1"
PARAMETER_NAME = "/employee-assistant/app-env"


def main():
    ssm = boto3.client("ssm", region_name=REGION)

    # Read the secrets supplied by GitHub Actions.
    secret_names = [
        "POSTGRES_PASSWORD",
        "NEO4J_PASSWORD",
        "APP_API_KEY",
        "OPENAI_API_KEY",
    ]

    settings = {}

    for name in secret_names:
        value = os.environ.get(name, "")

        # Our generated passwords and OpenAI key use these characters.
        # Reject unexpected characters without printing the secret.
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError(
                f"{name} is missing or contains unexpected characters. "
                "Check its GitHub secret value."
            )

        settings[name] = value

    settings["APP_USERNAME"] = "learner"
    settings["OPENAI_MODEL"] = "gpt-4.1-mini"
    settings["CORS_ORIGINS"] = (
        "http://localhost:8501,http://127.0.0.1:8501"
    )

    env_text = "\n".join(
        f"{name}={value}" for name, value in settings.items()
    ) + "\n"

    # Store settings securely. Never print env_text.
    ssm.put_parameter(
        Name=PARAMETER_NAME,
        Value=env_text,
        Type="SecureString",
        KeyId="alias/aws/ssm",
        Tier="Standard",
        Overwrite=True,
    )

    print("Application settings saved securely.", flush=True)

    image = (
        os.environ["ECR_REPOSITORY"]
        + ":"
        + os.environ["IMAGE_TAG"]
    )

    # read_text normalizes Windows line endings if necessary.
    script = Path("scripts/deploy.sh").read_text(encoding="utf-8")

    # Pass the image as $1 to the Bash script.
    # Secrets are not included in this command.
    command = (
        f"bash -c {shlex.quote(script)} deploy "
        f"{shlex.quote(image)}"
    )

    response = ssm.send_command(
        InstanceIds=[INSTANCE_ID],
        DocumentName="AWS-RunShellScript",
        Comment="Deploy Employee Knowledge Assistant",
        TimeoutSeconds=120,
        Parameters={
            "commands": [command],
            "executionTimeout": ["1800"],
        },
    )

    command_id = response["Command"]["CommandId"]
    print("Deployment command ID:", command_id, flush=True)

    deadline = time.monotonic() + 2100
    previous_status = None

    while time.monotonic() < deadline:
        try:
            result = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=INSTANCE_ID,
            )
        except ssm.exceptions.InvocationDoesNotExist:
            # AWS may need a few seconds to register the command.
            time.sleep(10)
            continue

        status = result["Status"]

        if status != previous_status:
            print("Deployment status:", status, flush=True)
            previous_status = status

        if status in {"Pending", "InProgress", "Delayed", "Cancelling"}:
            time.sleep(10)
            continue

        output = (
            result.get("StandardOutputContent", "")
            + "\n"
            + result.get("StandardErrorContent", "")
        )

        # Extra protection if a command unexpectedly echoes a secret.
        for name in secret_names:
            output = output.replace(settings[name], "***")

        print(output, flush=True)

        if status != "Success":
            raise SystemExit(f"Deployment failed: {status}")

        print("EC2 deployment succeeded.", flush=True)
        return

    raise SystemExit(
        "Stopped waiting for deployment. Check the command in "
        "AWS Systems Manager before starting another deployment."
    )


if __name__ == "__main__":
    main()
# /// script
# requires-python = ">=3.9,<3.15"
# dependencies = ["diagrams>=0.24"]
# ///
# Re-render with:  uv run <this file>     (needs Graphviz and schematize_style.py alongside)
from schematize_style import *

from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.integration import SQS
from diagrams.aws.management import OrganizationsAccount
from diagrams.aws.network import APIGateway, CloudFront
from diagrams.aws.storage import S3
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.client import Users

with diagram("Example - serverless API", "architecture-overview", direction="LR"):
    # nodeid= gives a component a stable identity, so board edits follow it even if its label changes
    users = Users("Users", nodeid="users")
    with group("AWS Cloud", "cloud", icon="diagram-icons/aws.png"):         # icons.py fetch aws
        with group("prod account", "account", icon=OrganizationsAccount):  # bundled icon class
            cdn = CloudFront("CloudFront", nodeid="cdn")
            site = S3("Web assets", nodeid="web-assets")
            api = APIGateway("HTTP API", nodeid="http-api")
            fn = Lambda("orders-api", nodeid="orders-api")
            queue = SQS("order-events", nodeid="order-events")
            worker = Lambda("fulfilment\nworker", nodeid="fulfilment-worker")
            table = Dynamodb("orders", nodeid="orders-table")
    with group("Delivery", "panel", fill="yellow"):
        ci = GithubActions("GitHub Actions", nodeid="github-actions")

    # main path first, in the order it happens
    users >> step(desc="Browser requests the web app") >> cdn
    cdn >> step(desc="CloudFront serves static assets from S3") >> site
    users >> step("HTTPS", "The app calls the orders API") >> api
    api >> step(desc="API Gateway invokes the handler") >> fn
    # then everything else
    fn >> data("put") >> table
    fn >> event("OrderPlaced") >> queue >> event() >> worker >> data("update") >> table
    ci >> ops("deploy", constraint="false") >> fn

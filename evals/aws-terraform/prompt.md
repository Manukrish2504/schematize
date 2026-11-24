Create these files, then draw the architecture of this codebase.

`main.tf`
```hcl
resource "aws_cloudfront_distribution" "web" { origin { domain_name = aws_s3_bucket.site.bucket_regional_domain_name } }
resource "aws_s3_bucket" "site" { bucket = "shop-web" }
resource "aws_apigatewayv2_api" "api" { name = "shop-api" protocol_type = "HTTP" }
resource "aws_lambda_function" "orders" { function_name = "orders" handler = "orders.handler" }
resource "aws_dynamodb_table" "orders" { name = "orders" hash_key = "id" }
resource "aws_sqs_queue" "events" { name = "order-events" }
resource "aws_lambda_function" "mailer" { function_name = "mailer" handler = "mailer.handler" }
resource "aws_lambda_event_source_mapping" "mailer" { event_source_arn = aws_sqs_queue.events.arn function_name = aws_lambda_function.mailer.arn }
```

`src/orders.py`
```python
import boto3, stripe
table = boto3.resource("dynamodb").Table("orders")
sqs = boto3.client("sqs")
def handler(event, ctx):
    stripe.PaymentIntent.create(amount=event["amount"], currency="usd")
    table.put_item(Item=event)
    sqs.send_message(QueueUrl=QUEUE_URL, MessageBody="OrderPlaced")
```

`src/mailer.py`
```python
import resend
def handler(event, ctx):
    resend.Emails.send({"to": event["email"], "subject": "Order confirmed"})
```

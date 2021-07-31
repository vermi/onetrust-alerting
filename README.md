# OneTrust Alerting Script

## Testing

### Run the script locally

You can easily run the script locally as well, but the results may not be in line with what you would expect if running via docker.

Simply comment out lines 161 and 162 in get-report-via-api.py and execute the script.
This assumes that both chrome and chromedriver are accessible from PATH. Otherwise, specify your install paths.

### Docker Testing Instructions

Since this container is designed to function within AWS Lambda, special testing procedures need to be done locally.

First, build and run the Docker image and use your local AWS credentials. (AWS CLI is required to be fully set up.)

```shell
docker build -t onetrust-alerts .
docker run -p 9000:8080 -v $HOME/.aws/credentials:/root/.aws/credentials:ro onetrust-alerts:latest
```

Then, in a separate terminal window, execute the Lambda simulation:

```shell
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'
```

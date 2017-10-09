import requests
import click
import json


def fetch(url):
    try:
        res = requests.get(url)
        if res.status_code == 200:
            return json.loads(res.text)
        else:
            return None
    except requests.exceptions.ConnectionError:
        return None


@click.command()
@click.option(
    '--host',
    default="http://localhost:5000",
    type=str,
    help='Event sampler address'
)
def main(**kwargs):
    ret = {}
    status = fetch(kwargs['host'] + "/status")
    histogram = fetch(kwargs['host'] + "/histogram")
    ret['histogram'] = histogram
    ret['status'] = status
    print(json.dumps(ret))


if __name__ == "__main__":
    main()

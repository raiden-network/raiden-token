from gevent import monkey
monkey.patch_all()
from populus import Project
import click
import gevent
import logging
from flask import Flask
from flask_restful import (
    Api,
)
from event_sampler.resources import LastBidSubmission, BidsHistogram
from event_sampler.sampler import EventSampler


@click.command()
@click.option(
    '--sample-period',
    default='5',
    help='How often to sample the blockchain'
)
@click.option(
    '--auction-address',
    help='Address of the auction contract'
)
@click.option(
    '--chain-name',
    default='kovan',
    help='Name of the chain'
)
@click.option(
    '--host',
    default='localhost',
    help='Address of the REST server'
)
@click.option(
    '--port',
    default=5000,
    help='Port of the REST server'
)
def main(sample_period, auction_address, chain_name, host, port):
    from gevent.pywsgi import WSGIServer
    app = Flask(__name__)
    api = Api(app)
    project = Project()
    with project.get_chain(chain_name) as chain:
        sampler = EventSampler(auction_address, chain)
        api.add_resource(LastBidSubmission, "/last_bid",
                         resource_class_kwargs={'sampler': sampler})
        api.add_resource(BidsHistogram, "/histogram",
                         resource_class_kwargs={'sampler': sampler})
        rest_server = WSGIServer((host, port), app)
        server_greenlet = gevent.spawn(rest_server.serve_forever)
        server_greenlet.join()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    main()

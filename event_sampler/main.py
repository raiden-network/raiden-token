from gevent import monkey
monkey.patch_all()
from populus import Project
import click
import gevent
import logging
import json
import os
from flask import Flask
from flask_restful import (
    Api,
)
from event_sampler.resources import BidsHistogram, AuctionStatus
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
    contracts_abi_path = os.path.join(os.path.dirname(__file__), '../build/contracts.json')
    auction_abi = json.load(open(contracts_abi_path))['DutchAuction']['abi']
    with project.get_chain(chain_name) as chain:
        auction_contract = chain.web3.eth.contract(abi=auction_abi, address=auction_address)
        sampler = EventSampler(auction_address, chain)
        api.add_resource(BidsHistogram, "/histogram",
                         resource_class_kwargs={'sampler': sampler})
        api.add_resource(AuctionStatus, "/status",
                         resource_class_kwargs={'auction_contract': auction_contract,
                                                'sampler': sampler})
        rest_server = WSGIServer((host, port), app)
        server_greenlet = gevent.spawn(rest_server.serve_forever)
        server_greenlet.join()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    main()

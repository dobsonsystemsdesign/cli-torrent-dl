import asyncio
import curses
import os
import subprocess
from functools import partial

import tordl.config as cfg
from tordl.app import App
from tordl.core import DlFacade, SearchEngineTest, Api
from tordl.rpc import JsonRpcServer, JsonRpcClient


def run_torrent_client(magnet_url):
    cmd = (cfg.TORRENT_CLIENT_CMD % magnet_url).split(' ')
    subprocess.Popen(
        cmd,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL
    )


def open_torrent_link(link):
    cmd = (cfg.BROWSER_CMD % link).split(' ')
    subprocess.Popen(
        cmd,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL
    )


def direct_download(st, loop=None):
    if not st:
        print('No search term defined, cannot use --download option.')
        exit(1)

    if not loop:
        loop = asyncio.get_event_loop()

    dl = DlFacade(loop)
    print('Searching %s for "%s"...' % (','.join(cfg.SEARCH_ENGINES), st))
    results = loop.run_until_complete(dl.search(st))
    if results:
        results = sorted(results, key=lambda r: r.seeders, reverse=True)
        result = results[0]
        print('Found "%s", seeds: %s, size: %s,  ' % (
            result.name, result.seeders, result.size
        ))
        if result.magnet_url:
            magnet_url = result.magnet_url
        else:
            print('Fetching magnet link...')
            magnet_url = loop.run_until_complete(dl.get_magnet_url(result))

        print('Running torrent client...')
        run_torrent_client(magnet_url)
    else:
        print('No results found.')


def test_search_engines(test_all=True, loop=None):
    if not loop:
        loop = asyncio.get_event_loop()

    test = SearchEngineTest(test_all, loop)
    loop.run_until_complete(test.run())


def run_api(st, pretty_json=True, loop=None):
    if not st:
        print('No search term defined, cannot use --api option.')
        exit(1)

    if not loop:
        loop = asyncio.get_event_loop()

    api = Api(
        None,
        cfg.FETCH_MISSING_MAGNET_LINKS,
        cfg.AGGREGATE_SAME_MAGNET_LINKS,
        cfg.FETCH_MAGNET_LINKS_CONCURRENCE,
        None,
        pretty_json
    )

    sr = loop.run_until_complete(api.fetch_with_magnet_links(st))

    print(sr)


def run_rpc_server(loop=None):
    loop = loop or asyncio.get_event_loop()
    server = JsonRpcServer(
        cfg.RPC_BIND_ADDRESS,
        cfg.RPC_BIND_PORT,
        api=Api(
            None,
            cfg.FETCH_MISSING_MAGNET_LINKS,
            cfg.AGGREGATE_SAME_MAGNET_LINKS,
            cfg.FETCH_MAGNET_LINKS_CONCURRENCE,
            None,
            cfg.PRETTY_JSON
        ),
        loop=loop
    )
    server.start()


def run_rpc_client(search_term, loop=None):
    if not search_term:
        print('No search term provided.')
        exit(1)

    loop = loop or asyncio.get_event_loop()
    c = JsonRpcClient(
        cfg.RPC_BIND_ADDRESS,
        cfg.RPC_BIND_PORT,
        cfg.RPC_USER,
        cfg.RPC_PASS,
        loop=loop
    )
    print(loop.run_until_complete(c.search(search_term)))


def run_curses_ui(st):
    os.environ.setdefault('ESCDELAY', '0')
    curses.wrapper(partial(App, search=st))

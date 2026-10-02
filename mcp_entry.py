import sys, multiprocessing
if __name__=='__main__':
    multiprocessing.freeze_support()
    from studio.mcp_server import run
    run('--headless' in sys.argv)

import time
from urllib.parse import urlparse


class FixedRateLoop(object):
    """
    A class for creating a fixed rate loop that compensates for function execution time.

    Revisions:
        2018FEB16 Armiger: Created
    """

    def __init__(self, dt):
        self.dt = dt
        self.enabled = True

    def loop(self, loop_function):
        """Runs the function provided at fixed rate. This is a blocking call"""

        time_elapsed = 0.0
        while self.enabled:
            try:
                # Fixed rate loop.  get start time, run model, get end time; delay for duration
                time_begin = time.time()

                # run the fixed rate function
                loop_function()

                time_end = time.time()
                time_elapsed = time_end - time_begin
                if self.dt > time_elapsed:
                    time.sleep(self.dt - time_elapsed)

                # print('{0} dt={1:6.3f}'.format(output['decision'], time_elapsed))

            except KeyboardInterrupt:
                break

        print("")
        print("Last time_elapsed was: ", time_elapsed)
        print("")
        print("Terminating loop...")
        print("")


def get_address(url):
    """
    convert address url string to get hostname and port as tuple for socket interface
    error checking port is native to urlparse

       # E.g. //127.0.0.1:1234 becomes:
       hostname = 127.0.0.1
       port = 1234

    :param url:
        url string in format '//0.0.0.0:80'
    :return:
        tuple of (hostname, port)
    """
    a = urlparse(url)

    return a.hostname, a.port

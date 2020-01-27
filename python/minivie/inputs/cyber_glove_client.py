from utilities.udp_comms import Udp
import time
import numpy as np


num_samples = 150
data_buffer = np.zeros((num_samples, 23))


def parse(data):
    global data_buffer
    x = np.frombuffer(data, dtype=np.uint8)
    data_buffer = np.roll(data_buffer, 1, axis=0)
    data_buffer[:1, :] = x[:23]

    print(x)


def old():
    # Setup Data Source
    a = Udp(('localhost', 16700))
    a.add_message_handler(parse)
    a.connect()
    print('Running...')
    time.sleep(3.0)
    print('Done')
    a.close()



def main():
    # Simple plot function for showing the EMG stream
    # Requires matplotlib
    #
    # To run from command line:
    # > python -m gui.test_live_plot.py
    #
    # Test function can also be 'double-clicked' to start

    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    from matplotlib import style

    # Ensure that the minivie specific modules can be found on path allowing execution from the 'inputs' folder

    # Setup Data Source
    # Setup Data Source
    a = Udp(('localhost', 16700))
    a.add_message_handler(parse)
    a.connect()

    style.use('dark_background')
    fig = plt.figure()
    ax1 = fig.add_subplot(1, 1, 1)
    fig.canvas.set_window_title('CyberGlove Preview')

    global data_buffer

    def animate(_):
        d = data_buffer * 0.1

        for iChannel in range(0, 23):
            d[:, iChannel] = d[::-1, iChannel] + (1 * (iChannel + 1))

        ax1.clear()
        ax1.plot(d)
        plt.ylim((0, 50))
        plt.xlabel('Samples')
        plt.ylabel('Channel')
        plt.title('CyberGlove Stream')
        # print('{:0.2f}'.format(m.get_data_rate_emg()))

    ani = animation.FuncAnimation(fig, animate, interval=150)
    plt.show()


if __name__ == '__main__':
    main()

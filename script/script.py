import logging, colorlog
import re, os, atpbar, time
import multiprocessing, threading
import pandas as pd
from datetime import datetime
from unidecode import unidecode
from ipywidgets import Label

from .pdf_scan.worker import Worker
from .pdf_scan.render_data import render_data

def initialize(logger: logging.Logger) -> tuple:
    """
    Function to initialize the script

    Args:
        logger (logging.Logger): Logger object

    Returns:
        tuple: Tuple containing start_time, logger, queue, qresult, CancelProcessEvent and render_date_label
    """
    # Setup
    start_time = datetime.now()

    logger.setLevel(logging.INFO)
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s[%(levelname)s] %(message)s'))
    logger.addHandler(handler)

    queue = multiprocessing.JoinableQueue()
    qresult = multiprocessing.SimpleQueue()

    CancelProcessEvent = multiprocessing.Event()

    render_date_label = Label(value="")

    return(start_time, logger, queue, qresult, CancelProcessEvent, render_date_label)

def main(opt, ini: tuple) -> list:
    """
    Main function of the script

    Args:
        opt (Option): Option object
        ini (tuple): Tuple containing start_time, logger, queue, qresult, CancelProcessEvent and render_date_label

    Returns:
        list: List of process
    """
    start_time, logger, queue, qresult, CancelProcessEvent, render_date_label = ini

    if not opt.first_initialization():
        logger.fatal("Script has already been initialized. Please restart the jupyter kernel to run it again.")
        raise UserWarning("Script has already been initialized. Please restart the jupyter kernel to run it again.")

    global option
    option = opt
    #option.keywords = pd.DataFrame(columns=['Word', 'Nb min', 'Nb max', 'Score if true', 'Score if false'],
    #            data=option.keywords)
    option.keywords = pd.read_csv(option.keyword_file, dtype={'Word': str, 'Nb min': float, 'Nb max': float, 'Score if true': int, 'Score if false': int})
    
    # Check if keywords are correctly formatted
    if option.check_keyword:
        logger.info("Checking keywords")
        for index, row in option.keywords.iterrows():
            if row['Nb min'] > row['Nb max']:
                raise ValueError(f"Word {row['Word']} has a min value greater than max value")
            text = unidecode(row['Word']).lower() # Retrait des accents et mise en minuscule
            text = re.sub('\s+','',text) # Retrait des espaces
            if text != row['Word']:
                logger.warning(f"Word \"{row['Word']}\" contains spaces or accents. It has been replaced by \"{text}\"")
                option.keywords.at[index, 'Word'] = text

    # Load old data
    if option.force_scan and option.clear_when_force_scan:
        old_data = pd.DataFrame(columns=['Filename', 'Url', 'Nb pages', 'Nb detected', 'Detected pages', 'N', 'Timestamp'])
        logger.warning("Clearing save.csv file and force scanning all pdf")
    
    elif os.path.isfile(option.data_folder + 'save.csv'):
        with open(option.data_folder + 'save.csv', 'r') as f:
            old_data = pd.read_csv(f, index_col=False, dtype={'Filename': str, 'Nb pages': int, 'Nb detected': int, 'Detected pages': str, 'N': bool, 'Timestamp': str})
            old_data['N'] = False
            old_data['Timestamp'] = pd.to_datetime(old_data['Timestamp'])
            logger.info(f"Loaded {len(old_data)} sets from save.csv")
    else:
        old_data = pd.DataFrame(columns=['Filename', 'Nb pages', 'Nb detected', 'Detected pages', 'N', 'Timestamp'])
        logger.warning("No save.csv file found")
    old_data['N'] = False

    # Scan pdf in pdf_folder and add all pdf to queue
    n_skip = 0
    logger.info(f"Scanning {option.pdf_folder} for pdf files")
    for pdf in os.listdir(option.pdf_folder):
        path = os.path.join(option.pdf_folder, pdf)
        if not path.endswith('.pdf'): # Ignore non pdf files
            continue
        if (not option.force_scan) and (pdf in old_data['Filename'].values): # Ignore already scanned pdf
            logger.info(f"Skipping {pdf} as it has already been scanned")
            n_skip += 1
            continue
        logger.info(f"Adding {pdf} to queue")
        queue.put({"path": os.path.relpath(path), "timestamp": datetime.now(), "url": ""})

    # Initialize workers
    if option.watch_import:
        n_thread = max(option.n_workers, 1)
        logger.info(f">> Watching {option.pdf_folder} for new pdf and scans")
    else:
        n_thread = min(max(option.n_workers, 1), queue.qsize())

    n_pdf = queue.qsize()
    logger.info(f">> {n_skip} pdf files have been skipped")
    if option.watch_import:
        logger.info(f">> Adding {n_pdf} sets into a data queue that {n_thread} workers will work. Watching enabled for new pdf...")
    else:
        logger.info(f">> Adding {n_pdf} sets into a data queue that {n_thread} workers will work from until empty")

    as_started = [False for _ in range(n_thread)]
    process = []
    reporter = atpbar.find_reporter()
    qlog = multiprocessing.SimpleQueue()
    threading.Thread(target=qlogger, args=(as_started, qlog, logger, CancelProcessEvent)).start()
    for i in range(len(as_started)):
        work = Worker(option, qresult, qlog, queue, reporter)
        p = multiprocessing.Process(target=work.run, args=(CancelProcessEvent,), name=f"P{i+1}")
        p.start()
        process.append(p)
    
    while not all(as_started): # Wait for all workers to start
        time.sleep(0.1)

    # Depend if we watch for new pdf and scans or not
    if option.watch_import:
        # Watch for new pdf and scans
        threading.Thread(target=watcher, args=(CancelProcessEvent, logger, option, qresult, start_time, old_data, render_date_label)).start()

    else:
        # Only one scan, wait for all workers to finish
        queue.join()
        atpbar.flush() # Flush atpbar (progress bar)
        logger.info("All workers have finished")

        # Render data
        render_data(option, qresult, start_time, old_data)
        logger.info(f"Results have been written to {option.result_file}")
        logger.info(f"Program finished in {str(datetime.now() - start_time).split('.')[0]}")

    return process # Return process to be able to cancel them with the cancel button

def qlogger(as_started: list, qlog: multiprocessing.SimpleQueue, logger: logging.Logger, CancelProcessEvent: multiprocessing.Event) -> None:
    """
    Function to log messages from qlog. Use to log messages from multiprocessing.Process workers

    Args:
        as_started (list): List of boolean to know if a worker has started
        qlog (multiprocessing.SimpleQueue): Queue containing log messages
        logger (logging.Logger): Logger object
        CancelProcessEvent (multiprocessing.Event): Event to cancel the process
    """
    while not CancelProcessEvent.is_set():
        level, message = qlog.get()
        match level:
            case 'debug':
                logger.debug(message)
            case 'info':
                logger.info(message)
            case 'warning':
                logger.warning(message)
            case 'error':
                logger.error(message)
            case 'fatal':
                logger.fatal(message)
            case 'exception':
                logger.exception(message)
            case 'started':
                logger.info(f"[P{message}] Worker has started")
                as_started[message-1] = True
            case _:
                logger.warning(f"Unknown level {level} with message {message}")

def watcher(CancelProcessEvent: multiprocessing.Event, logger: logging.Logger, *args) -> None:
    """
    Function to render new pdf. Only used if watch_import is True

    Args:
        CancelProcessEvent (multiprocessing.Event): Event to cancel the process
        logger (logging.Logger): Logger object
        *args: Arguments to pass to render_data. Must contain option, qresult, start_time and old_data. See render_data for more information
    """
    result_data = []
    while not CancelProcessEvent.is_set():
        result_data = render_data(*args, row_result=result_data)
    logger.info("Watcher has been cancelled")
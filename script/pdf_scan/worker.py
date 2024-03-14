import os, re, multiprocessing, atpbar, PyPDF2
import pandas as pd
from unidecode import unidecode

import time

class Worker(object):
    worker_id = 1
    def __init__(self, option, result: multiprocessing.SimpleQueue, logger: multiprocessing.SimpleQueue, queue: multiprocessing.JoinableQueue, reporter: atpbar.reporter.ProgressReporter) -> None:
        self.option = option
        self.result = result
        self.logger = logger
        self.queue = queue
        self.reporter = reporter

        self.worker_id = Worker.worker_id
        Worker.update_id()
        
        #self.result = pd.DataFrame(columns=['Filename', 'Nb pages', 'Nb detected', 'Detected pages'])
    
    @classmethod
    def update_id(cls) -> None:
        cls.worker_id += 1

    def run(self, CancelProcessEvent: multiprocessing.Event) -> None:
        output = pd.DataFrame(columns=['Filename', 'Nb pages', 'Nb detected', 'Detected pages', 'N', 'Timestamp'])
        atpbar.register_reporter(self.reporter)
        self.logger.put(('started', self.worker_id))
        time.sleep(0.5)
        while True:
            try: # try to catch and print errors in the logger
                if CancelProcessEvent.is_set():
                    self.logger.put(('info', f"[P{self.worker_id}] Worker has been cancelled"))
                    break
                try:
                    pdf_data = self.queue.get_nowait()
                except multiprocessing.queues.Empty:
                    if self.option.watch_import:
                        time.sleep(1)
                        continue
                    else:
                        self.logger.put(('info', f"[P{self.worker_id}] Queue is empty: Stoping worker"))
                        self.result.put(output)
                        break
                
                pdf_data = self.scan_task(pdf_data)
                new_output = self.format_task(pdf_data)

                if self.option.watch_import:
                    self.result.put(new_output)
                else:
                    output = pd.concat([output, new_output], ignore_index=True)
                self.queue.task_done()
            except Exception as error:
                self.logger.put(('exception', error))
                try:
                    self.queue.task_done()
                except ValueError:
                    pass
    
    def test(self):
        for _ in atpbar.atpbar(range(50), name=f"{self.worker_id}"):
            time.sleep(0.5)  
    
    def scan_task(self, pdf_data: dict) -> dict:
        with open(pdf_data['path'], 'rb') as pdfFileObj:
            pdf = PyPDF2.PdfReader(pdfFileObj)

            pdf_data.update({
                "filename": os.path.basename(pdf_data['path']),
                "abs_path": os.path.abspath(pdf_data['path']),
                "n_pages": len(pdf.pages),
                "detected_page": pd.DataFrame({'Page': [], 'Score': []})
            })

            for k in atpbar.atpbar(range(pdf_data['n_pages']), name=f"[P{self.worker_id}] {pdf_data['filename']}"):
                text = pdf.pages[k].extract_text()
                score = self.analyse_text(text)
                if score >= self.option.threshold:
                    pdf_data['detected_page'] = pd.concat([
                        pdf_data['detected_page'], 
                        pd.DataFrame({'Page': [k+1], 'Score': [score]}) # +1 car les pdf commence page 1 dans les Reader
                    ])

        return pdf_data

    def analyse_text(self, text: str) -> int:
        text = unidecode(text).lower() # Retrait des accents et mise en minuscule
        text = re.sub('\s+','',text) # Retrait des espaces

        def counter(text: str, row: pd.Series) -> int:        
            if row['Nb min'] <= text.count(row['Word']) <= row['Nb max']:
                return row['Score if true']
            else:
                return row['Score if false']
            
        return self.option.keywords.apply(lambda x: counter(text, x), axis=1).sum()

    def format_task(self, pdf_data: dict) -> pd.DataFrame:
        best_score = pdf_data['detected_page']['Score'].max()
        
        if len(pdf_data['detected_page']) > 0:
            pdf_data['detected_page']['Page'] = pdf_data['detected_page'].apply(
                lambda x: '<a class="{max_score}" title="Score: {score}" href="{abs_path}#page={page}" target="_blank">{page}</a>'.format(
                    abs_path=pdf_data['abs_path'],
                    page=int(x['Page']),
                    score=x['Score'],
                    max_score='max-score' if x['Score'] == best_score else ''
                ),
                axis=1
            )
            pdf_data['detected_page'].sort_values(by='Score', ascending=False, inplace=True)
        else:
            pdf_data['detected_page']['Page'] = ""

        pdf_data['url'] = f'<a class="filename" href="{pdf_data["url"]}" target="_blank">{pdf_data["filename"]}</a>'

        return pd.DataFrame({
            'Filename': [pdf_data['filename']],
            'Url': [pdf_data['url']],
            'Nb pages': [pdf_data['n_pages']],
            'Nb detected': [len(pdf_data['detected_page'])],
            'Detected pages': [' '.join(list(pdf_data['detected_page']['Page']))],
            'N': [True],
            'Timestamp': [pdf_data['timestamp']]
        })
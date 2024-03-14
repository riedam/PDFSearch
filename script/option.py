from inspect import signature
inf = float('inf')

class Option:
    """
    Class containing all the options for the script
    """
    _first_initialization = True

    def __init__(self,
                 pdf_folder: str,
                 data_folder: str,
                 result_file: str,
                 keyword_file: str,
                 watch_import: bool,
                 force_scan: bool,
                 clear_when_force_scan: bool,
                 sort_data: str,
                 n_workers: int,
                 check_keyword: bool,
                 threshold: int,
                 watcher_year_interval: list,
                 request_timeout: int | None,
                 ) -> None:
        """
        Args:
            pdf_folder (str): Dossier contenant les pdf à analyser
            data_folder (str): Dossier contenant les données sauvegardées
            result_file (str): Fichier html contenant les résultats
            keyword_file (str): Fichier csv contenant les mots clés
            watch_import (bool): Surveille le dossier pdf_folder pour de nouveaux pdf
            force_scan (bool): Force la réanalyse des pdf même si save.csv est présent
            clear_when_force_scan (bool): Efface les données sauvegardées si force_scan est activé
            sort_data ['Filename', 'Timestamp]: Manière de trier les données. 'alpha' pour trier par ordre alphabétique, 'date' pour trier par date
            n_workers (int): Nombre de threads à utiliser
            check_keyword (bool): Vérifie que les mots clés sont correctement formatés
            threshold (int): Seuil de détection des mots clés
            request_timeout (int|None): Temps d'attente avant qu'une requête n'expire. None pour désactiver

        Returns:
            None
        """
        # Check if all parameters are of the correct type
        local_vars = locals()
        for param in signature(Option).parameters:
            normal_type = signature(Option).parameters[param].annotation
            if not isinstance(local_vars[param], normal_type):
                raise ValueError(f"Option parameter {param} must be of type {normal_type}")
        
        self.pdf_folder = pdf_folder
        self.data_folder = data_folder

        if not result_file.endswith('.html'):
            raise ValueError("result_file must be an .html file")
        self.result_file = result_file
        if not keyword_file.endswith('.csv'):
            raise ValueError("keyword_file must be an .txt file")
        self.keyword_file = keyword_file

        self.watch_import = watch_import
        self.force_scan = force_scan
        self.clear_when_force_scan = clear_when_force_scan

        if sort_data not in ['Filename', 'Timestamp']:
            raise ValueError("sort_data must be either 'Filename' or 'Timestamp'")
        self.sort_data = sort_data

        self.n_workers = n_workers

        self.check_keyword = check_keyword
        self.threshold = threshold

        if not (isinstance(watcher_year_interval[0], int) and isinstance(watcher_year_interval[1], int)):
            raise ValueError("watcher_year_interval must be a list of integers")
        if watcher_year_interval[0] >= watcher_year_interval[1]:
            raise ValueError("watcher_year_interval[0] must be smaller or equal to watcher_year_interval[1]")
        self.watcher_year_interval = watcher_year_interval

        if not (request_timeout > 0 or request_timeout is None):
            raise ValueError("request_timeout must be a positive integer")
        self.request_timeout = request_timeout
    
    @classmethod
    def first_initialization(cls):
        """
        Check if the class has already been initialized
        
        Returns:
            bool: True if the class has already been initialized, False otherwise
        """
        if cls._first_initialization:
            cls._first_initialization = False
            return True
        else:
            return False
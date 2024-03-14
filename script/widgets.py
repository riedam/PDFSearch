import os
from validators import url as is_url
from datetime import datetime

import ipywidgets as widgets

from .import_pdf.pdf_import import url_request

def my_widgets(opt, ini: tuple, process: list) -> tuple:
    """
    Args:
        opt (Option): Option object
        ini (tuple): Tuple containing logger, queue and CancelProcessEvent
        process (list): List of process
    
    Returns:
        tuple: Tuple containing widgets and functions
    """
    _, logger, queue, qresult,  CancelProcessEvent, render_date_label = ini

    universtity = widgets.Text(placeholder="Nom de l'université", description="Name", layout=widgets.Layout(width="auto"))    
    year = widgets.IntSlider(min=opt.watcher_year_interval[0],
                             max=opt.watcher_year_interval[1],
                             step=1,
                             value=(opt.watcher_year_interval[1]-opt.watcher_year_interval[0])//2 + opt.watcher_year_interval[0],
                             description="Year",
                             layout=widgets.Layout(width="auto")
                             )
    url = widgets.Text(placeholder="http://exemple.com", description="URL", layout=widgets.Layout(width="auto"))
    button_add = widgets.Button(description="Add pdf", button_style="success", layout=widgets.Layout(width="100%"))
    button_force_add = widgets.Button(description="Force download", disabled=True, layout=widgets.Layout(width="100%"))

    button_force_render = widgets.Button(description="Force render", button_style="info", layout=widgets.Layout(width="auto"))
    button_change_sort_mode = widgets.Button(description=f"Change sort mode ({opt.sort_data})", button_style="", layout=widgets.Layout(width="auto"))

    button_cancel = widgets.Button(description="Cancel all threads", button_style="warning", layout=widgets.Layout(width="auto"))

    output = widgets.Output()

    app = widgets.AppLayout(
        header=None,
        left_sidebar=widgets.VBox([
                universtity,
                year,
                url,
                widgets.HBox([button_add, button_force_add], layout=widgets.Layout(width="auto"))
            ], layout=widgets.Layout(width="auto")),
        center=widgets.Label(""),
        right_sidebar=widgets.VBox([
                button_force_render,
                button_change_sort_mode,
                render_date_label,
                button_cancel
            ], layout=widgets.Layout(width="auto")),
        footer=None,
        pane_widths=[3, 1, 2]
    )

    def add_script(force: bool = False):
        with output:
            output.clear_output()
            button_add.disabled = True
            button_force_add.disabled = True
            button_force_add.button_style = ''
            if universtity.value == "":
                print("Name cannot be empty")
                button_add.disabled = False
                return
            if not is_url(url.value):
                print("URL is not valid")
                button_add.disabled = False
                return
            name = f"{universtity.value}_{year.value}.pdf"
            print(f"Adding {name}...")
            if os.path.isfile(opt.pdf_folder + name):
                if force:
                    print(f"{name} already exists. Forcing download...")
                else:
                    button_force_add.disabled = False
                    button_force_add.button_style = 'warning'
                    print(f"{name} already exists. Use force download to download it again.")
                    button_add.disabled = False
                    return
            result = url_request(opt, url.value, name)
            if result:
                path = opt.pdf_folder + name
                queue.put({
                    "path": os.path.relpath(path),
                    "timestamp": datetime.now(),
                    "url": url.value
                    })
                print(f"PDF added to {path}")
                print(f"PDF added to queue (Queue length: {queue.qsize()})")
                year.value += 1
                url.value = ''
            button_add.disabled = False

    def button_add_func(b):
        add_script(False)
    
    def button_force_add_func(b):
        add_script(True)

    def button_force_render_func(b):
        qresult.put(None)
        button_force_render.disabled = True
        button_change_sort_mode.disabled = True
        button_force_render.description = "Rendering..."

    def render_label_observer(change):
        if change['new'] == "Last render: in progress...":
            button_force_render.description = "Rendering..."
            button_force_render.disabled = True
            button_change_sort_mode.disabled = True
        else:
            button_force_render.description = "Force render"
            button_force_render.disabled = False
            button_change_sort_mode.disabled = False
    
    render_date_label.observe(render_label_observer, names="value")

    def button_change_sort_mode_func(b):
        if opt.sort_data == "Timestamp":
            opt.sort_data = "Filename"
            button_change_sort_mode.description = "Change sort mode (Filename)"
        else:
            opt.sort_data = "Timestamp"
            button_change_sort_mode.description = "Change sort mode (Timestamp)"
    
    def button_cancen_func(b):
        if button_cancel.button_style != "danger":
            button_cancel.description = "Confirm cancel"
            button_cancel.button_style = "danger"
            return
        for p in process:
            p.kill()
            logger.info(f"[{p.name}] has been canceled")
        CancelProcessEvent.set()
        logger.info("All threads have been canceled")
        app_to_hide = [universtity, year, url, button_add, button_force_add, button_force_render, button_change_sort_mode, button_cancel]
        for b in app_to_hide:
            b.disabled = True

    return (
        (app, output),
        (
            (button_add, button_add_func),
            (button_force_add, button_force_add_func),
            (button_force_render, button_force_render_func),
            (button_change_sort_mode, button_change_sort_mode_func),
            (button_cancel, button_cancen_func)
        )
    )
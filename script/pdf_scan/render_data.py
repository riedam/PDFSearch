import multiprocessing, time, os
import pandas as pd
from datetime import datetime
from ipywidgets import Label

def render_data(option, qresult: multiprocessing.SimpleQueue, start_time: datetime, old_data: pd.DataFrame, render_date_label: Label = None, row_result: list = []) -> list:
    with open('script/html/base.html', 'r') as f:
        final_html = f.read()

    # Get all data
    if option.watch_import:
        # Block function for the first result. Use when watching mode is enabled.
        # Usefull to have not infinit loop when qresult is empty
        new = qresult.get()
        render_date_label.value = "Last render: in progress..."
        if new is not None: # None can be used to force render when watching mode is enabled
            row_result.append(new)
        time.sleep(5) # Wait for the next result, use to not render every time # TODO: Create option for this

    render_date_label.value = "Last render: in progress..."
    while not qresult.empty():
        new = qresult.get()
        if new is not None: # None can be used to force render when watching mode is enabled
            row_result.append(new)

    if len(row_result) != 0 and len(old_data) != 0:
        result_data = pd.concat(row_result, ignore_index=True)
        result_data = pd.concat([result_data, old_data], ignore_index=True)

    elif len(row_result) != 0:
        result_data = pd.concat(row_result, ignore_index=True)
    
    else:
        result_data = old_data

    result_data.to_csv(option.data_folder + 'save.csv', index=False)

    # Format results

    # result_data['Url'] = result_data.apply(
    #     lambda x: '<a class="filename" href="{url}" target="_blank">{filename}</a>'.format(
    #         url=x['Url'],
    #         filename=x['Filename']
    #         ),
    #     axis=1
    # )
    result_data = result_data.astype({'N': int})
    result_data.sort_values(by=['Timestamp'], ascending=False, inplace=True)
    result_data.reset_index(drop=True, inplace=True)
    result_data.drop_duplicates(subset=['Filename'], keep='first', inplace=True)
    result_data.sort_values(by=['N'], ascending=False, inplace=True)
    result_data.sort_values(by=option.sort_data, ascending=(option.sort_data=='Filename'), inplace=True)
    result_data.drop(columns=['Filename', 'Timestamp'], inplace=True)
    result_data.rename(columns={'Url': 'Filename'}, inplace=True)

    # Convert to html
    html_result = result_data.to_html(index=False, escape=False, classes="full-width")

    if option.watch_import:
        time_by_scan = ''
    else:
        time_by_scan = f" ({str((datetime.now() - start_time)/max(1, len(result_data) - len(old_data))).split('.')[0]}/scan)"
    replace_key = [
        ("table", html_result),
        ("keywords", option.keywords.to_html(index=False, escape=False)),
        ("n_pdf", f"{len(result_data)} (Scan: {len(result_data) - len(old_data)}, Skip: {len(old_data)})"),
        ("total_pages", f"{result_data['Nb pages'].sum()} (Scan: {result_data[result_data['N'] == 1]['Nb pages'].sum()}, Skip: {result_data[result_data['N'] == 0]['Nb pages'].sum()})"),
        ("detected_pages", f"{result_data['Nb detected'].sum()} (Scan: {result_data[result_data['N'] == 1]['Nb detected'].sum()}, Skip: {result_data[result_data['N'] == 0]['Nb detected'].sum()})"),
        ("threshold", option.threshold),
        ("thread", f"{option.n_workers} (cpu: {os.cpu_count()})"),
        ("time", str(datetime.now() - start_time).split(".")[0]),
        ("time_by_scan", time_by_scan),
        ("render_timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ]
    for key, value in replace_key:
        final_html = final_html.replace("{{"+ key +"}}", str(value))
    
    with open('result.html', 'w') as f:
        f.write(final_html)
    
    render_date_label.value = f"Last render: {datetime.now().strftime('%H:%M:%S')}"
    return row_result # Only usefull when watching mode is enabled

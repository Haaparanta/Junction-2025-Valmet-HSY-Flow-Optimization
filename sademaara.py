import requests
from xml.etree import ElementTree
from datetime import datetime, timedelta

def print_rain_measurements(station_id, start_time, end_time):
    url = (
        "https://opendata.fmi.fi/wfs"
        "?service=WFS"
        "&version=2.0.0"
        "&request=getFeature"
        "&storedquery_id=fmi::observations::weather::multipointcoverage"
        f"&fmisid={station_id}"
        f"&starttime={start_time}"
        f"&endtime={end_time}"
    )

    r = requests.get(url)
    r.raise_for_status()
    root = ElementTree.fromstring(r.content)

    ns = {
        'gml': "http://www.opengis.net/gml/3.2",
        'swe': "http://www.opengis.net/swe/2.0"
    }

    rain_values = []

    # Extract rainfall values
    for datablock in root.findall(".//gml:rangeSet/gml:DataBlock", ns):
        axis_elem = datablock.find(".//gml:tupleList", ns)
        if axis_elem is None:
            axis_elem = datablock.find(".//gml:doubleOrNilReasonTupleList", ns)
        if axis_elem is None:
            continue

        lines = axis_elem.text.strip().split("\n")
        for line in lines:
            parts = line.split()
            try:
                rain = float(parts[-1])
                rain_values.append(rain)
            except:
                continue

    if not rain_values:
        print("No rainfall data found for this period.")
        return
    return rain_values

def downsample_10min_to_15min(rain_values):
    downsampled = []
    i = 0
    n = len(rain_values)
    while i < n:
        # Take first value as-is
        downsampled.append(rain_values[i])
        i += 1
        # Take next two values and average
        if i + 1 < n:
            avg = (rain_values[i] + rain_values[i+1]) / 2
            downsampled.append(avg)
            i += 2
    return downsampled

if __name__ == "__main__":
    station_id = 852678 #Nuuksio
    #MAX 168H
    start = "2024-11-15T00:00:00Z"
    end   = "2024-11-21T23:59:00Z"

    rain_values_10 = print_rain_measurements(station_id, start, end)
    rain_values_15 = downsample_10min_to_15min(rain_values_10)
    print(rain_values_15)
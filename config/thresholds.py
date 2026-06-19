# S5P GEE band names and QA thresholds
S5P_BANDS = {
    'NO2': {
        'collection': 'COPERNICUS/S5P/OFFL/L3_NO2',
        'band': 'tropospheric_NO2_column_number_density',
        'qa_threshold': 0.75
    },
    'SO2': {
        'collection': 'COPERNICUS/S5P/OFFL/L3_SO2',
        'band': 'SO2_column_number_density',
        'qa_threshold': 0.50
    },
    'CO': {
        'collection': 'COPERNICUS/S5P/OFFL/L3_CO',
        'band': 'CO_column_number_density',
        'qa_threshold': 0.50
    },
    'O3': {
        'collection': 'COPERNICUS/S5P/OFFL/L3_O3',
        'band': 'O3_column_number_density',
        'qa_threshold': 0.50
    },
    'HCHO': {
        'collection': 'COPERNICUS/S5P/OFFL/L3_HCHO',
        'band': 'tropospheric_HCHO_column_number_density',
        'qa_threshold': 0.50
    }
}

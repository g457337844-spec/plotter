from pathlib import Path
import math, pytest
from studio.models import DataError, Options
from studio.parsers import parse_xps_rows, parse_xrd, parse_reference, numeric_tokens
from studio.planning import display_values, validate_selection

def xps(rows): return parse_xps_rows(rows,path=Path('sample.xlsx'),sheet='O1s Scan')

def test_measured_header_wins_over_index():
    ds=xps([['Binding Energy','Index','Measured Counts','FitPeak1'],['eV','','Counts/s','Counts/s'],[530,1,100,80],[531,2,120,95]])
    assert ds.measured.values==[100,120]
    assert ds.warnings

def test_units_and_blank_avantage_header():
    ds=xps([['Binding Energy',None,None,'Fit envelope','Fit peak A'],['eV',None,'Counts / s','Counts/s','Counts/s'],[530,None,100,99,70],[531,None,120,121,80]])
    assert ds.measured.source_column==3
    assert len(ds.curves)==3

def test_no_units_row_does_not_eat_first_point():
    ds=xps([['Binding Energy','Counts'],[530,100],[531,200]])
    assert ds.x==[530,531]; assert ds.x_unit=='eV'; assert ds.metadata['data_row']==2

def test_no_units_does_not_invent_count_rate():
    ds=xps([['Binding Energy','Intensity'],[530,100],[531,200]])
    assert ds.measured.unit=='a.u.' and ds.warnings

def test_overlay_incompatible_units_rejected():
    a=xps([['Binding Energy','Counts'],[530,100],[531,200]])
    b=parse_xps_rows([['Binding Energy','Intensity'],[530,100],[531,200]],path=Path('b.xlsx'),sheet='O1s')
    with pytest.raises(DataError,match='单位'): validate_selection([a,b],Options(mode='overlay'))

def test_missing_peak_keeps_whole_curve():
    ds=xps([['Binding Energy','Counts','Fit peak A','Fit peak B'],[530,100,50,60],[531,110,55,None],[532,120,60,65]])
    assert [c.role for c in ds.curves].count('peak')==2
    assert ds.curves[-1].values==[60,None,65]; assert ds.warnings

def test_empty_row_does_not_truncate_data():
    ds=xps([['Binding Energy','Counts'],[530,100],[None,None],[532,200]])
    assert ds.x==[530,532]

def test_unknown_columns_require_mapping():
    with pytest.raises(DataError,match='不明确'):
        xps([['Binding Energy','Index','Unknown'],[530,1,100],[531,2,200]])
    ds=parse_xps_rows([['Binding Energy','Index','Unknown'],[530,1,100],[531,2,200]],path=Path('s.xlsx'),sheet='O1s',mapping={'y_column':3})
    assert ds.measured.values==[100,200]

@pytest.mark.parametrize('value',[math.inf,math.nan,'1e999',True])
def test_invalid_range_rejected(value):
    with pytest.raises(DataError): Options.from_dict({'x_min':0,'x_max':value})

def test_partial_range_rejected():
    with pytest.raises(DataError): Options.from_dict({'x_min':5})

def test_strict_xrd_tokens():
    assert numeric_tokens('10, 100oops') is None
    assert numeric_tokens('10, 100, 1')==(10,100)
    with pytest.raises(DataError): parse_xrd(Path('s.txt'),'\n'.join([f'{i} 100' for i in range(10)]+['10 100oops']))

def test_nonfinite_xrd_is_error():
    with pytest.raises(DataError): parse_xrd(Path('s.txt'),'\n'.join([f'{i} 100' for i in range(10)]+['10 1e999']))

def test_spaced_pdf_header():
    ds=parse_reference(Path('p.txt'),'PDF# 21-1276:\nTitanium oxide\nTiO2\n2-Theta d I ( h k l)\n25.3 3.5 100 (1 0 1)\n48 2 20 (2 0 0)')
    assert ds.metadata['card_number']=='21-1276'

def test_constant_normalization_is_finite():
    ds=parse_xrd(Path('s.txt'),'\n'.join(f'{i} 100' for i in range(10)))
    assert display_values(ds,Options(normalize_xrd=True))==[0]*10

def test_reference_is_optional():
    ds=parse_xrd(Path('s.txt'),'\n'.join(f'{i} {i*i}' for i in range(10)))
    assert len(validate_selection([ds],Options()))==1

def test_empty_visible_range_rejected_before_origin():
    ds=parse_xrd(Path('s.txt'),'\n'.join(f'{i} 100' for i in range(10)))
    with pytest.raises(DataError): validate_selection([ds],Options(x_min=20,x_max=30))

def test_overlay_never_mixes_xps_levels():
    a=xps([['Binding Energy','Counts'],[530,100],[531,200]])
    b=parse_xps_rows([['Binding Energy','Counts'],[280,100],[281,200]],path=Path('s.xlsx'),sheet='C1s Scan')
    assert len(validate_selection([a,b],Options(mode='overlay')))==2

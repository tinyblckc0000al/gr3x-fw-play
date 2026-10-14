#!/usr/bin/env python3
"""Bridge GR3-LUTSmith look.json to gr3-film-mods v16 fit.json (OFFLINE ONLY).

This prepares data for testing; it does not modify firmware, invoke the assembler,
write camera files, or establish that the two pipelines are equivalent on hardware.

Usage:
 python lutsmith_to_filmmods16.py from.look.json out.fit.json --identity-hue
 python lutsmith_to_filmmods16.py from.look.json out.fit.json --report out.report.json

IMPORTANT: film-mods v16 stores each of 12 sector matrices as nine signed int8
coefficients with a Q10/4 quantization and rows summing to Q10=1024. This
projection may change the LUTSmith fit; compare on independent test samples.
"""
import argparse, json, math
from pathlib import Path


def matrix_shape(m, nrows, ncols, label):
    if not isinstance(m, list) or len(m) != nrows or any(not isinstance(r,list) or len(r)!=ncols for r in m):
        raise ValueError(f'{label} must be {nrows}x{ncols}')
    for row in m:
        for x in row:
            if not isinstance(x,(float,int)) or not math.isfinite(x):
                raise ValueError(f'{label} must contain finite numbers')


def identity_hue():
    return [[[1024 if i==j else 0 for j in range(3)] for i in range(3)] for _ in range(12)]


def q10_v16_sector(look):
    q = look.get('hue_sectors') or {}
    q = q.get('matrices_q10')
    if q is None:
        return None
    if not isinstance(q,list) or len(q)!=12:
        raise ValueError('hue_sectors.matrices_q10 must have 12 sectors')
    out, errors = [], []
    for s, mat in enumerate(q):
        matrix_shape(mat,3,3,f'hue sector {s}')
        quant=[]
        for i, row in enumerate(mat):
            if any(int(x) != x for x in row):
                raise ValueError(f'hue sector {s} must have integer Q10 values')
            if sum(row)!=1024:
                raise ValueError(f'hue sector {s}, row {i} must sum to 1024')
            off=[0,0,0]
            for j in range(3):
                if j!=i:
                    raw=round(int(row[j])/4)
                    if not -127 <= raw <=127:
                        raise ValueError(f'hue sector {s} row {i} col {j} out of signed-int8 range')
                    off[j]=raw*4
            raw_diag=-sum(off)//4
            if not -127<=raw_diag<=127:
                raise ValueError(f'hue sector {s} row {i} diagonal delta overflows int8')
            off[i]=1024-sum(off)
            quant.append(off)
            errors += [abs(int(row[j])-off[j]) for j in range(3)]
        out.append(quant)
    return out, {'max_abs_q10':max(errors,default=0),'mean_abs_q10':sum(errors)/max(len(errors),1),
                  'max_abs_float':max(errors,default=0)/1024,'identity':all(out[s]==identity_hue()[s] for s in range(12))}


def convert(look, use_identity_hue=False):
    M=look['matrix_q13']
    matrix_shape(M,3,3,'matrix_q13')
    if any(int(x)!=x or abs(x)>32767 for row in M for x in row):
        raise ValueError('matrix_q13 must contain signed int16 integers')
    # film-mods make_film.py::q13_matrix re-quantizes and normalizes row sums.
    if any(sum(row)!=8192 for row in M):
        raise ValueError('matrix_q13 rows must sum to 8192')
    C=look.get('curves')
    if C is None:
        raise ValueError('look has no curves: v16 requires 3x256 explicit tone curves')
    matrix_shape(C,3,256,'curves')
    if any(int(x)!=x or not 0<=x<=16383 for row in C for x in row):
        raise ValueError('curves must contain u16 values within 0..16383')
    fit={'matrix':[[x/8192 for x in row] for row in M],
         'presets':[{'curves':C}]}
    result=q10_v16_sector(look)
    if result is None:
        if not use_identity_hue:
            raise ValueError('no hue sectors in look.json; use --identity-hue to explicitly synthesize identity sectors')
        fit['hue_q10']=identity_hue()
        hue_stats={'source':'identity-generated','max_abs_q10':0,'mean_abs_q10':0.0,'max_abs_float':0.0,'identity':True}
    else:
        fit['hue_q10'],hue_stats=result
        hue_stats['source']='LUTSmith hue_sectors projected into v16 int8 range'
    P=look.get('post_matrix_q9')
    if P is not None:
        matrix_shape(P,3,3,'post_matrix_q9')
        if any(int(x)!=x or abs(x)>32767 for row in P for x in row):
            raise ValueError('post_matrix_q9 values must be signed int16 integers')
        if any(sum(row)!=512 for row in P):
            raise ValueError('post_matrix_q9 rows must sum to 512')
        fit['post_q512']=P
    fit['_conversion_provenance']={
      'source_tool':look.get('tool'),'source_file':(look.get('lut') or {}).get('file'),
      'source_sha256':(look.get('lut') or {}).get('sha256'),
      'warning':'Offline schema conversion only. Film-mods v16 hue sector semantics and runtime state must be verified independently.'}
    report={'hue_quantization':hue_stats,'has_post_matrix':P is not None,
            'source_curve_mode':look.get('curve_mode'),'source_fit_score':look.get('scores'),
            'warnings':[
             'v16 uses a different hue representation and shares GR IV-derived controls; equivalent appearance is NOT established.',
             'Quantized hue coefficients may alter colors. Evaluate deltaE00 after conversion before compiling firmware.',
             'Curve mapping and image processing order must be tested on the same simulated input.',
             'Do not flash images generated from unverified conversion.'
             ]}
    return fit,report


def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input_look',type=Path)
    ap.add_argument('output_fit',type=Path)
    ap.add_argument('--identity-hue',action='store_true',help='Fill 12 sectors with identity when the source look has no hue')
    ap.add_argument('--report',type=Path,help='Write quantified error report to JSON')
    ns=ap.parse_args()
    look=json.loads(ns.input_look.read_text(encoding='utf-8'))
    fit,report=convert(look, ns.identity_hue)
    ns.output_fit.parent.mkdir(parents=True,exist_ok=True)
    ns.output_fit.write_text(json.dumps(fit,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    if ns.report:
        ns.report.parent.mkdir(parents=True,exist_ok=True)
        ns.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Wrote',ns.output_fit)
    print('Hue quantization',report['hue_quantization'])
    print('Post matrix',report['has_post_matrix'])
    print('WARNING: offline schema conversion only; no firmware is produced.')

if __name__=='__main__':
    main()

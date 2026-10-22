"""Independent v4.1 diagonal seed math followed by unchanged v4 context math."""
import numpy as np
from reference_v3 import window_math as old_math, windows, median_image
from reference_v4 import packed_fields,context_image

CANDIDATES={'A':18,'B':19}

def window_math(values,threshold=64,diagonal_min_diff=19,enabled=True):
    base=old_math(values,threshold,18,0,True)
    a=np.asarray(values,dtype=np.int32);gx,gy=base['gx'],base['gy']
    dx=a[...,:,2]-a[...,:,0];dy=a[...,2,:]-a[...,0,:];d=diagonal_min_diff
    sx=((gx>0)&((dx>=d).sum(axis=-1)>=2))|((gx<0)&((dx<=-d).sum(axis=-1)>=2))
    sy=((gy>0)&((dy>=d).sum(axis=-1)>=2))|((gy<0)&((dy<=-d).sum(axis=-1)>=2))
    ax,ay=np.abs(gx),np.abs(gy)
    band=(ax!=0)&(ay!=0)&(np.maximum(ax,ay)<=2*np.minimum(ax,ay))
    added=(base['l1']>threshold)&sx&sy&band&enabled
    return {**base,'base_v3_seed':base['edge'],'diagonal_seed':added,'diagonal_support':sx&sy,
            'diagonal_band':band,'edge':base['edge']|added}

def image_math(gray,threshold=64,diagonal_min_diff=19):
    median=median_image(gray)
    m=window_math(windows(median),threshold,diagonal_min_diff)
    seed=m['edge'];old=m['base_v3_seed']
    packed=packed_fields(m['center'],m['gx'],m['gy'],m['l1'],seed,threshold,16)
    post=context_image(packed);edge=post['edge']
    return {**m,**post,'median':median,'v3_edge':old,'seed':seed,'packed':packed,
            'added':~old&edge,'removed':old&~edge}

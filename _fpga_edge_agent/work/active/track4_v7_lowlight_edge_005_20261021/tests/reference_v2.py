"""Independent integer image/window reference; no RTL pipeline emulation."""
import numpy as np

KX=np.array([[-1,0,1],[-2,0,2],[-1,0,1]],dtype=np.int32)
KY=KX.T

def windows(image, radius=1):
    return np.lib.stride_tricks.sliding_window_view(np.pad(image,radius,mode='edge'),(2*radius+1,2*radius+1))

def median_image(gray):
    h,w=gray.shape
    return np.sort(windows(gray).reshape(h,w,9),axis=-1)[...,4]

def window_math(values, threshold=64, difference=16, enabled=True):
    a=np.asarray(values,dtype=np.int32)
    gx=np.einsum('...ij,ij->...',a,KX,dtype=np.int32)
    gy=np.einsum('...ij,ij->...',a,KY,dtype=np.int32)
    dx=a[..., :,2]-a[..., :,0]
    dy=a[..., 2,:]-a[..., 0,:]
    sx=((gx>0)&((dx>=difference).sum(axis=-1)>=2))|((gx<0)&((dx<=-difference).sum(axis=-1)>=2))
    sy=((gy>0)&((dy>=difference).sum(axis=-1)>=2))|((gy<0)&((dy<=-difference).sum(axis=-1)>=2))
    support=((np.abs(gx)>=np.abs(gy))&sx)|((np.abs(gy)>=np.abs(gx))&sy)
    l1=np.abs(gx)+np.abs(gy)
    edge=(l1>threshold)&(support if enabled else True)
    return dict(center=a[...,1,1],gx=gx,gy=gy,l1=l1,edge=edge,support=support)

def image_math(gray, threshold=64, difference=16, enabled=True):
    median=median_image(gray)
    return dict(median=median,**window_math(windows(median),threshold,difference,enabled))

def record_pair(pair, threshold, difference, enabled):
    m=window_math(pair,threshold,difference,enabled)
    def packed(field,bits):return sum((int(v)&((1<<bits)-1))<<(bits*i) for i,v in enumerate(field))
    window=sum(int(v)<<(8*i) for i,v in enumerate(np.asarray(pair).reshape(-1)))
    result=packed(m['center'],8)
    for field in ('gx','gy','l1'):result=(result<<22)|packed(m[field],11)
    result=(result<<2)|packed(m['edge'],1)
    return (window<<84)|result

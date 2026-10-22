"""Approved v4 spatial rule, independent array math; no RTL timing emulation."""
import numpy as np
from reference_v3 import image_math as v3_image, windows

CANDIDATES={'A':32,'B':16}

def packed_fields(center,gx,gy,l1,seed,threshold=64,drop=16):
    gx,gy=np.asarray(gx,dtype=np.int32),np.asarray(gy,dtype=np.int32)
    ax,ay=np.abs(gx),np.abs(gy)
    direction=np.where(2*ay<ax,0,np.where(2*ax<ay,2,np.where((gx<0)==(gy<0),1,3)))
    direction=np.where((gx==0)&(gy==0),0,direction).astype(np.uint16)
    weak=(np.asarray(l1)>max(int(threshold)-drop,0))&((gx!=0)|(gy!=0))
    return (np.asarray(center,dtype=np.uint16)|(direction<<8)|
            (weak.astype(np.uint16)<<10)|(np.asarray(seed,dtype=np.uint16)<<11))

def context_image(packed):
    a=np.asarray(packed,dtype=np.uint16)
    seed=(a&2048)!=0;weak=(a&1024)!=0;direction=(a>>8)&3
    # Outside the image is never independent seed evidence.
    s=np.pad(seed,1,mode='constant');d=np.pad(direction,1,mode='edge')
    h,w=a.shape
    at=lambda p,dy,dx:p[1+dy:1+dy+h,1+dx:1+dx+w]
    neighbors=sum(at(s,dy,dx).astype(np.int32) for dy in (-1,0,1) for dx in (-1,0,1) if (dy,dx)!=(0,0))>0
    repair=np.zeros_like(seed)
    for k,pair in {0:((-1,0),(1,0)),2:((0,-1),(0,1)),1:((-1,1),(1,-1)),3:((-1,-1),(1,1))}.items():
        (dy1,dx1),(dy2,dx2)=pair
        compatible1=((at(d,dy1,dx1).astype(np.int32)-direction.astype(np.int32))%4)!=2
        compatible2=((at(d,dy2,dx2).astype(np.int32)-direction.astype(np.int32))%4)!=2
        repair|=(direction==k)&at(s,dy1,dx1)&at(s,dy2,dx2)&compatible1&compatible2
    edge=np.where(seed,neighbors,weak&repair)
    return dict(edge=edge,removed=seed&~edge,added=~seed&edge,direction=direction,weak=weak)

def image_math(gray,threshold=64,drop=16):
    base=v3_image(gray,threshold,18,0)
    packed=packed_fields(base['center'],base['gx'],base['gy'],base['l1'],base['edge'],threshold,drop)
    return {**base,'v3_edge':base['edge'],'packed':packed,**context_image(packed)}

def filter_windows(values,x_even,y,width,height):
    """Independent scalar coordinate rule for arbitrary two-lane window vectors."""
    result=[]
    pairs={0:((-1,0),(1,0)),2:((0,-1),(0,1)),1:((-1,1),(1,-1)),3:((-1,-1),(1,1))}
    for lane,a in enumerate(values):
        x=x_even+lane;cy=y;c=int(a[1,1]);direction=(c>>8)&3
        def seed_at(dy,dx):
            return 0<=x+dx<width and 0<=cy+dy<height and bool(int(a[dy+1,dx+1])&2048)
        if c&2048:
            edge=any(seed_at(dy,dx) for dy in (-1,0,1) for dx in (-1,0,1) if (dy,dx)!=(0,0))
        else:
            edge=bool(c&1024)
            for dy,dx in pairs[direction]:
                neighbor=int(a[dy+1,dx+1]);delta=(((neighbor>>8)&3)-direction)%4
                edge=edge and seed_at(dy,dx) and delta!=2
        result.append((c&255,int(edge)))
    return result

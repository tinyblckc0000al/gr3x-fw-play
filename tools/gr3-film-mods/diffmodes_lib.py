def ranges(a,b):
    r=[];i=0;n=len(a)
    while i<n:
        if a[i]!=b[i]:
            j=i
            while j<n and (a[j]!=b[j] or (j+8<n and a[j:j+8]!=b[j:j+8])): j+=1
            r.append((i,j)); i=j
        else: i+=1
    return r

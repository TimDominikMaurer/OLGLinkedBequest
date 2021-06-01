# Numba JIT compiled functions by Jeppe Druedahl https://sites.google.com/view/jeppe-druedahl/
import numpy as np
import math
from numba import njit, boolean, int32, double, void, int64

# interpolation functions:
@njit(int64(int64,int64,double[:],double))
def binary_search(imin,Nx,x,xi):
        
    # a. checks
    if xi <= x[0]:
        return 0
    elif xi >= x[Nx-2]:
        return Nx-2
    
    # b. binary search
    half = Nx//2
    while half:
        imid = imin + half
        if x[imid] <= xi:
            imin = imid
        Nx -= half
        half = Nx//2
        
    return imin


@njit(double(double[:],double[:],double[:,:],double,double,int32,int32),fastmath=True)
def _interp_2d(grid1,grid2,value,xi1,xi2,j1,j2):
    """ 2d interpolation for one point with known location
        
    Args:

        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (2d)
        xi1 (double): input point
        xi2 (double): input point
        j1 (int): location in grid 
        j2 (int): location in grid

    Returns:

        yi (double): output

    """

    # a. left/right
    nom_1_left = grid1[j1+1]-xi1
    nom_1_right = xi1-grid1[j1]

    nom_2_left = grid2[j2+1]-xi2
    nom_2_right = xi2-grid2[j2]

    # b. interpolation
    denom = (grid1[j1+1]-grid1[j1])*(grid2[j2+1]-grid2[j2])
    nom = 0
    for k1 in range(2):
        nom_1 = nom_1_left if k1 == 0 else nom_1_right
        for k2 in range(2):
            nom_2 = nom_2_left if k2 == 0 else nom_2_right                    
            nom += nom_1*nom_2*value[j1+k1,j2+k2]

    return nom/denom

@njit(double(double[:],double[:],double[:,:],double,double),fastmath=True)
def interp_2d(grid1,grid2,value,xi1,xi2):
    """ 2d interpolation for one point
        
    Args:

        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (2d)
        xi1 (double): input point
        xi2 (double): input point

    Returns:

        yi (double): output

    """

    # a. search in each dimension
    j1 = binary_search(0,grid1.size,grid1,xi1)
    j2 = binary_search(0,grid2.size,grid2,xi2)

    return _interp_2d(grid1,grid2,value,xi1,xi2,j1,j2)

@njit(double(int32[:],double[:],double[:],double[:,:],double,double),fastmath=True)
def interp_2d_to_rep(js,grid1,grid2,value,xi1,xi2):
    """ 2d interpolation for one point (with later repition without search)
        
    Args:

        js (numpy.nddarray): information on search
        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (2d)
        xi1 (double): input point
        xi2 (double): input point

    Returns:

        yi (double): output

    """

    # a. search in each dimension
    js[0] = j1 = binary_search(0,grid1.size,grid1,xi1)
    js[1] = j2 = binary_search(0,grid2.size,grid2,xi2)

    return _interp_2d(grid1,grid2,value,xi1,xi2,j1,j2)

@njit(double(int32[:],double[:],double[:],double[:,:],double,double),fastmath=True)
def interp_2d_from_rep(js,grid1,grid2,value,xi1,xi2):
    """ 2d interpolation for one point without search
        
    Args:

        js (numpy.nddarray): information on search
        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (2d)
        xi1 (double): input point
        xi2 (double): input point

    Returns:

        yi (double): output

    """

    # a. search in each dimension
    j1 = js[0]
    j2 = js[1]

    return _interp_2d(grid1,grid2,value,xi1,xi2,j1,j2)

@njit(void(double[:],double[:],double[:,:],double[:],double[:],double[:]),fastmath=True)
def interp_2d_vec(grid1,grid2,value,xi1,xi2,yi):
    """ 2d interpolation for vector of points
        
    Args:

        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (2d)
        xi1 (numpy.ndarray): input vector
        xi2 (numpy.ndarray): input vector
        yi (numpy.ndarray): output vector

    """

    for i in range(yi.size):
        yi[i] = interp_2d(grid1,grid2,value,xi1[i],xi2[i])
    
        

@njit(int32[:](double[:],double,int32),fastmath=True)
def interp_2d_prep(grid1,xi1,Nyi):
    """ preperation for 2d interpolation of only last dimension
        
    Args:

        grid1 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (2d)
        xi1 (double): input point
        Nyi (int): number of points to be evaluated

    Returns:

        prep (numpy.ndarray): information for remaining operations

    """

    # a. search in non-last dimensions
    j1 = binary_search(0,grid1.size,grid1,xi1)
    
    # b. prep
    prep = np.zeros((1+Nyi,),dtype=np.int32)
    prep[Nyi+0] = j1

    return prep

@njit(void(int32[:],double[:],double[:],double[:,:],double,double[:],double[:],boolean,boolean),fastmath=True)
def _interp_2d_only_last_vec(prep,grid1,grid2,value,xi1,xi2,yi,monotone,search):
    """ 2d interpolation for vector of points
        
    Args:

        prep (numpy.ndarray): information for remaining operations
        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (2d)
        xi1 (double): input point
        xi2 (numpy.ndarray): vector of points
        yi (numpy.ndarray): output vector
        monotone (bool): indicator for whether xi2 is monotone
        search (bool): indicator for whether search is needed at all

    """

    # a. search in last dimension
    Nyi = yi.size
    j1 = prep[Nyi + 0]
    if search:
        for i in range(Nyi):
            if monotone and i > 0:
                j2 = prep[i-1]
                while xi2[i] >= grid2[j2+1] and j2 < grid2.size-2:
                    j2 += 1
                prep[i] = j2
            else:
                prep[i] = binary_search(0,grid2.size,grid2,xi2[i])

    # b. initialize
    for i in range(yi.size):
        yi[i] = 0.0

    # c. interpolation
    nom_1_left = grid1[j1+1]-xi1
    nom_1_right = xi1-grid1[j1]

    denom = (grid1[j1+1]-grid1[j1])
    for k1 in range(2):
        nom_1 = nom_1_left if k1 == 0 else nom_1_right   
        for i in range(yi.size):
            for k2 in range(2):
                j2 = prep[i]
                nom_2 = grid2[j2+1]-xi2[i] if k2 == 0 else xi2[i]-grid2[j2]            
                yi[i] += nom_1*nom_2*value[j1+k1,j2+k2]

    for i in range(Nyi):
        j2 = prep[i]
        yi[i] /= denom*(grid2[j2+1]-grid2[j2])

@njit(void(int32[:],double[:],double[:],double[:,:],double,double[:],double[:]),fastmath=True)
def interp_2d_only_last_vec(prep,grid1,grid2,value,xi1,xi2,yi):
    """ 2d interpolation for vector of points
        
    Args:

        prep (numpy.ndarray): information for remaining operations
        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (2d)
        xi1 (double): input point
        xi2 (numpy.ndarray): vector of points
        yi (numpy.ndarray): output vector

    """

    _interp_2d_only_last_vec(prep,grid1,grid2,value,xi1,xi2,yi,False,True)

@njit(void(int32[:],double[:],double[:],double[:,:],double,double[:],double[:]),fastmath=True)
def interp_2d_only_last_vec_mon(prep,grid1,grid2,value,xi1,xi2,yi):
    """ 2d interpolation for vector of points where xi2 is monotone
        
    Args:

        prep (numpy.ndarray): information for remaining operations
        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (2d)
        xi1 (double): input point
        xi2 (numpy.ndarray): vector of points
        yi (numpy.ndarray): output vector

    """

    _interp_2d_only_last_vec(prep,grid1,grid2,value,xi1,xi2,yi,True,True)    

@njit(void(int32[:],double[:],double[:],double[:,:],double,double[:],double[:]),fastmath=True)
def interp_2d_only_last_vec_mon_rep(prep,grid1,grid2,value,xi1,xi2,yi):
    """ 2d interpolation for vector of points where xi2 is monotone and search is not needed
        
    Args:

        prep (numpy.ndarray): information for remaining operations
        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (2d)
        xi1 (double): input point
        xi2 (numpy.ndarray): vector of points
        yi (numpy.ndarray): output vector

    """

    _interp_2d_only_last_vec(prep,grid1,grid2,value,xi1,xi2,yi,True,False)       




@njit(double(double[:],double[:],double))
def interp_linear_1d_scalar(grid,value,xi):
    """ raw 1D interpolation """

    # a. search
    ix = binary_search(0,grid.size,grid,xi)
    
    # b. relative positive
    rel_x = (xi - grid[ix])/(grid[ix+1]-grid[ix])
    
    # c. interpolate
    return value[ix] + rel_x * (value[ix+1]-value[ix])




@njit
def interp_linear_1d(grid,value,xi):

    yi = np.empty(xi.size)

    for ixi in range(xi.size):

        # c. interpolate
        yi[ixi] = interp_linear_1d_scalar(grid,value,xi[ixi])
    
    return yi


# State space
@njit
def nonlinspace(x_min, x_max, n, phi):
    """ like np.linspace between with unequal spacing
    phi = 1 -> eqaul spacing
    phi up -> more points closer to minimum
    """
    assert x_max > x_min
    assert n >= 2
    assert phi >= 1
 
    # 1. recursion
    y = np.empty(n)
 
    y[0] = x_min
    for i in range(1, n):
        y[i] = y[i-1] + (x_max-y[i-1]) / (n-i)**phi
    
    # 3. assert increaing
    assert np.all(np.diff(y) > 0)
 
    return y

@njit
def gauss_hermite(n):
    # a. calculations
    i = np.arange(1,n)
    a = np.sqrt(i/2)
    CM = np.diag(a,1) + np.diag(a,-1)
    L,V = np.linalg.eig(CM)
    I = L.argsort()
    V = V[:,I].T

    # b. nodes and weights
    x = L[I]
    w = np.sqrt(math.pi)*V[:,0]**2

    return x,w


@njit(double(double[:],double[:],double[:],double[:,:,:],double,double,double,int32,int32,int32),fastmath=True)
def _interp_3d(grid1,grid2,grid3,value,xi1,xi2,xi3,j1,j2,j3):
    """ 3d interpolation for one point with known location
        
    Args:

        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        grid3 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (3d)
        xi1 (double): input point
        xi2 (double): input point
        xi3 (double): input point
        j1 (int): location in grid 
        j2 (int): location in grid
        j3 (int): location in grid

    Returns:

        yi (double): output

    """

    # a. left/right
    nom_1_left = grid1[j1+1]-xi1
    nom_1_right = xi1-grid1[j1]

    nom_2_left = grid2[j2+1]-xi2
    nom_2_right = xi2-grid2[j2]

    nom_3_left = grid3[j3+1]-xi3
    nom_3_right = xi3-grid3[j3]

    # b. interpolation
    denom = (grid1[j1+1]-grid1[j1])*(grid2[j2+1]-grid2[j2])*(grid3[j3+1]-grid3[j3])
    nom = 0
    for k1 in range(2):
        nom_1 = nom_1_left if k1 == 0 else nom_1_right
        for k2 in range(2):
            nom_2 = nom_2_left if k2 == 0 else nom_2_right       
            for k3 in range(2):
                nom_3 = nom_3_left if k3 == 0 else nom_3_right               
                nom += nom_1*nom_2*nom_3*value[j1+k1,j2+k2,j3+k3]

    return nom/denom

@njit(double(double[:],double[:],double[:],double[:,:,:],double,double,double),fastmath=True)
def interp_3d(grid1,grid2,grid3,value,xi1,xi2,xi3):
    """ 3d interpolation for one point
        
    Args:

        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        grid3 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (3d)
        xi1 (double): input point
        xi2 (double): input point
        xi3 (double): input point

    Returns:

        yi (double): output

    """

    # a. search in each dimension
    j1 = binary_search(0,grid1.size,grid1,xi1)
    j2 = binary_search(0,grid2.size,grid2,xi2)
    j3 = binary_search(0,grid3.size,grid3,xi3)

    return _interp_3d(grid1,grid2,grid3,value,xi1,xi2,xi3,j1,j2,j3)

@njit(void(double[:],double[:],double[:],double[:,:,:],double[:],double[:],double[:],double[:]),fastmath=True)
def interp_3d_vec(grid1,grid2,grid3,value,xi1,xi2,xi3,yi):
    """ 3d interpolation for vector of points
        
    Args:

        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        grid3 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (3d)
        xi1 (numpy.ndarray): input vector
        xi2 (numpy.ndarray): input vector
        xi3 (numpy.ndarray): input vector
        yi (numpy.ndarray): output vector

    """

    for i in range(yi.size):
        yi[i] = interp_3d(grid1,grid2,grid3,value,xi1[i],xi2[i],xi3[i])

@njit(int32[:](double[:],double[:],double,double,int32),fastmath=True)
def interp_3d_prep(grid1,grid2,xi1,xi2,Nyi):
    """ preperation for 3d interpolation of only last dimension
        
    Args:

        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (3d)
        xi1 (double): input point
        xi2 (double): input point
        Nyi (int): number of points to be evaluated

    Returns:

        prep (numpy.ndarray): information for remaining operations

    """

    # a. search in non-last dimensions
    j1 = binary_search(0,grid1.size,grid1,xi1)
    j2 = binary_search(0,grid2.size,grid2,xi2)
    
    # b. prep
    prep = np.zeros((2+Nyi,),dtype=np.int32)
    prep[Nyi+0] = j1
    prep[Nyi+1] = j2

    return prep

@njit(double(int32[:],double[:],double[:],double[:],double[:,:,:],double,double,double),fastmath=True)
def interp_3d_only_last(prep,grid1,grid2,grid3,value,xi1,xi2,xi3):
    """ 3d interpolation of only last dimension
        
    Args:

        prep (numpy.ndarray): information for remaining operations
        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        grid3 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (3d)
        xi1 (double): input point
        xi2 (double): input point
        xi3 (double): input point

    Returns:

        yi (double): output

    """

    # a. search in last dimension
    j1 = prep[0]
    j2 = prep[1]
    j3 = binary_search(0,grid3.size,grid3,xi3)
    
    return _interp_3d(grid1,grid2,grid3,value,xi1,xi2,xi3,j1,j2,j3)

@njit(void(int32[:],double[:],double[:],double[:],double[:,:,:],double,double,double[:],double[:],boolean,boolean),fastmath=True)
def _interp_3d_only_last_vec(prep,grid1,grid2,grid3,value,xi1,xi2,xi3,yi,monotone,search):
    """ 3d interpolation for vector of points
        
    Args:

        prep (numpy.ndarray): information for remaining operations
        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        grid3 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (3d)
        xi1 (double): input point
        xi2 (double): input point
        xi3 (numpy.ndarray): input vector
        yi (numpy.ndarray): output vector
        monotone (bool): indicator for whether xi3 is monotone
       search (bool): indicator for whether search is needed at all

    """

    # a. search in last dimension
    Nyi = yi.size
    j1 = prep[Nyi + 0]
    j2 = prep[Nyi + 1]    
    if search:
        for i in range(Nyi):
            if monotone and i > 0:
                j3 = prep[i-1]
                while xi3[i] >= grid3[j3+1] and j3 < grid3.size-2:
                    j3 += 1
                prep[i] = j3
            else:
                prep[i] = binary_search(0,grid3.size,grid3,xi3[i])

    # b. initialize
    for i in range(yi.size):
        yi[i] = 0.0

    # c. interpolation
    nom_1_left = grid1[j1+1]-xi1
    nom_1_right = xi1-grid1[j1]

    nom_2_left = grid2[j2+1]-xi2
    nom_2_right = xi2-grid2[j2]
    
    denom = (grid1[j1+1]-grid1[j1])*(grid2[j2+1]-grid2[j2])
    for k1 in range(2):
        nom_1 = nom_1_left if k1 == 0 else nom_1_right
        for k2 in range(2):
            nom_2 = nom_2_left if k2 == 0 else nom_2_right      
            for i in range(yi.size):
                for k3 in range(2):
                    j3 = prep[i]
                    nom_3 = grid3[j3+1]-xi3[i] if k3 == 0 else xi3[i]-grid3[j3]            
                    yi[i] += nom_1*nom_2*nom_3*value[j1+k1,j2+k2,j3+k3]

    for i in range(Nyi):
        j3 = prep[i]
        yi[i] /= denom*(grid3[j3+1]-grid3[j3])

@njit(void(int32[:],double[:],double[:],double[:],double[:,:,:],double,double,double[:],double[:]),fastmath=True)
def interp_3d_only_last_vec(prep,grid1,grid2,grid3,value,xi1,xi2,xi3,yi):
    """ 3d interpolation for vector of points
        
    Args:

        prep (numpy.ndarray): information for remaining operations
        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        grid3 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (3d)
        xi1 (double): input point
        xi2 (double): input point
        xi3 (numpy.ndarray): input vector
        yi (numpy.ndarray): output vector

    """

    _interp_3d_only_last_vec(prep,grid1,grid2,grid3,value,xi1,xi2,xi3,yi,False,True)

@njit(void(int32[:],double[:],double[:],double[:],double[:,:,:],double,double,double[:],double[:]),fastmath=True)
def interp_3d_only_last_vec_mon(prep,grid1,grid2,grid3,value,xi1,xi2,xi3,yi):
    """ 3d interpolation for vector of points where xi3 is monotone
        
    Args:

        prep (numpy.ndarray): information for remaining operations
        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        grid3 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (3d)
        xi1 (double): input point
        xi2 (double): input point
        xi3 (numpy.ndarray): input vector
        yi (numpy.ndarray): output vector

    """

    _interp_3d_only_last_vec(prep,grid1,grid2,grid3,value,xi1,xi2,xi3,yi,True,True)    

@njit(void(int32[:],double[:],double[:],double[:],double[:,:,:],double,double,double[:],double[:]),fastmath=True)
def interp_3d_only_last_vec_mon_rep(prep,grid1,grid2,grid3,value,xi1,xi2,xi3,yi):
    """ 3d interpolation for vector of points where xi3 is monotone and search is not needed
        
    Args:

        prep (numpy.ndarray): information for remaining operations
        grid1 (numpy.ndarray): 1d grid
        grid2 (numpy.ndarray): 1d grid
        grid3 (numpy.ndarray): 1d grid
        value (numpy.ndarray): value array (3d)
        xi1 (double): input point
        xi2 (double): input point
        xi3 (numpy.ndarray): input vector
        yi (numpy.ndarray): output vector

    """

    _interp_3d_only_last_vec(prep,grid1,grid2,grid3,value,xi1,xi2,xi3,yi,True,False)     







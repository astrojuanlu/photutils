# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This module defines interpolator classes for Background2D.
"""

import numpy as np

from ..utils import ShepardIDWInterpolator

__all__ = ['BkgZoomInterpolator', 'BkgIDWInterpolator']

__doctest_requires__ = {('BkgZoomInterpolator'): ['scipy']}


class BkgZoomInterpolator:
    """
    This class generates full-sized background and background RMS images
    from lower-resolution mesh images using the `~scipy.ndimage.zoom`
    (spline) interpolator.

    This class must be used in concert with the `Background2D` class.

    Parameters
    ----------
    order : int, optional
        The order of the spline interpolation used to resize the
        low-resolution background and background RMS mesh images.  The
        value must be an integer in the range 0-5.  The default is 3
        (bicubic interpolation).

    mode : {'reflect', 'constant', 'nearest', 'wrap'}, optional
        Points outside the boundaries of the input are filled according
        to the given mode.  Default is 'reflect'.

    cval : float, optional
        The value used for points outside the boundaries of the input if
        ``mode='constant'``. Default is 0.0
    """

    def __init__(self, order=3, mode='reflect', cval=0.0):
        self.order = order
        self.mode = mode
        self.cval = cval

    def __call__(self, mesh, bkg2d_obj):
        """
        Resize the 2D mesh array.

        Parameters
        ----------
        mesh : 2D `~numpy.ndarray`
            The low-resolution 2D mesh array.

        bkg2d_obj : `Background2D` object
            The `Background2D` object that prepared the ``mesh`` array.

        Returns
        -------
        result : 2D `~numpy.ndarray`
            The resized background or background RMS image.
        """
        mesh = np.asanyarray(mesh)
        if np.ptp(mesh) == 0:
            return np.zeros_like(bkg2d_obj.data) + np.min(mesh)

        from scipy.ndimage import zoom

        if bkg2d_obj.edge_method == 'pad':
            # The mesh is first resized to the larger padded-data size
            # (i.e., zoom_factor should be an integer) and then cropped
            # back to the final data size.
            zoom_factor = bkg2d_obj.box_size
            result = zoom(mesh, zoom_factor, order=self.order, mode=self.mode,
                          cval=self.cval)
            return result[0:bkg2d_obj.data.shape[0],
                          0:bkg2d_obj.data.shape[1]]
        else:
            # The mesh is resized directly to the final data size.
            zoom_factor = np.array(bkg2d_obj.data.shape) / mesh.shape
            return zoom(mesh, zoom_factor, order=self.order, mode=self.mode,
                        cval=self.cval)


class BkgIDWInterpolator:
    """
    This class generates full-sized background and background RMS images
    from lower-resolution mesh images using inverse-distance weighting
    (IDW) interpolation (`~photutils.utils.ShepardIDWInterpolator`).

    This class must be used in concert with the `Background2D` class.

    Parameters
    ----------
    leafsize : float, optional
        The number of points at which the k-d tree algorithm switches
        over to brute-force. ``leafsize`` must be positive.  See
        `scipy.spatial.cKDTree` for further information.

    n_neighbors : int, optional
        The maximum number of nearest neighbors to use during the
        interpolation.

    power : float, optional
        The power of the inverse distance used for the interpolation
        weights.

    reg : float, optional
        The regularization parameter. It may be used to control the
        smoothness of the interpolator.
    """

    def __init__(self, leafsize=10, n_neighbors=10, power=1.0, reg=0.0):
        self.leafsize = leafsize
        self.n_neighbors = n_neighbors
        self.power = power
        self.reg = reg

    def __call__(self, mesh, bkg2d_obj):
        """
        Resize the 2D mesh array.

        Parameters
        ----------
        mesh : 2D `~numpy.ndarray`
            The low-resolution 2D mesh array.

        bkg2d_obj : `Background2D` object
            The `Background2D` object that prepared the ``mesh`` array.

        Returns
        -------
        result : 2D `~numpy.ndarray`
            The resized background or background RMS image.
        """
        mesh = np.asanyarray(mesh)
        if np.ptp(mesh) == 0:
            return np.zeros_like(bkg2d_obj.data) + np.min(mesh)

        yxpos = np.column_stack(bkg2d_obj._mesh_yxpos)
        mesh1d = mesh[bkg2d_obj._mesh_idx]
        interp_func = ShepardIDWInterpolator(yxpos, mesh1d,
                                             leafsize=self.leafsize)

        # the position coordinates used when calling the interpolator
        ny, nx = bkg2d_obj.data.shape
        yi, xi = np.mgrid[0:ny, 0:nx]
        yx_indices = np.column_stack((yi.ravel(), xi.ravel()))
        data = interp_func(yx_indices,
                           n_neighbors=self.n_neighbors, power=self.power,
                           reg=self.reg)

        return data.reshape(bkg2d_obj.data.shape)

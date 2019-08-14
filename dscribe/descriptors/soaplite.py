import os
import glob
import math

import numpy as np

from scipy.special import gamma
from scipy.linalg import sqrtm, inv

from ctypes import *

from dscribe.utils.geometry import get_extended_system


def _format_ase2clusgeo(obj, all_atomtypes=None):
    """ Takes an ase Atoms object and returns numpy arrays and integers
    which are read by the internal clusgeo. Apos is currently a flattened
    out numpy array

    Args:
        obj():
        all_atomtypes():
        sort():
    """
    # Atoms metadata
    totalAN = len(obj)
    if all_atomtypes is not None:
        atomtype_set = set(all_atomtypes)
    else:
        atomtype_set = set(obj.get_atomic_numbers())

    atomtype_lst = np.sort(list(atomtype_set))
    n_atoms_per_type_lst = []
    pos_lst = []
    for atomtype in atomtype_lst:
        condition = obj.get_atomic_numbers() == atomtype
        pos_onetype = obj.get_positions()[condition]
        n_onetype = pos_onetype.shape[0]

        # Store data in lists
        pos_lst.append(pos_onetype)
        n_atoms_per_type_lst.append(n_onetype)

    typeNs = n_atoms_per_type_lst
    Ntypes = len(n_atoms_per_type_lst)
    atomtype_lst
    Apos = np.concatenate(pos_lst).ravel()
    return Apos, typeNs, Ntypes, atomtype_lst, totalAN


def get_soap_locals_gto(obj, Hpos, alp, bet, rcut=5.0, nMax=5, Lmax=5, crossOver=True, all_atomtypes=None, eta=1.0):
    """Get the RBF basis SOAP output for the given positions in a finite system.

    Args:
        obj(ase.Atoms): Atomic structure for which the SOAP output is
            calculated.
        Hpos: Positions at which to calculate SOAP
        alp: Alphas
        bet: Betas
        rCut: Radial cutoff.
        nMax: Maximum number of radial basis functions
        Lmax: Maximum spherical harmonics degree
        crossOver:
        all_atomtypes: Can be used to specify the atomic elements for which to
            calculate the output. If given the output is calculated only for the
            given species and is ordered by atomic number.
        eta: The gaussian smearing width.

    Returns:
        np.ndarray: SOAP output for the given positions.
    """
    rCutHard = rcut + 5
    assert Lmax <= 9, "l cannot exceed 9. Lmax={}".format(Lmax)
    assert Lmax >= 0, "l cannot be negative.Lmax={}".format(Lmax)
    assert rCutHard < 17.0001, "hard radius cuttof cannot be larger than 17 Angs. rCut={}".format(rCutHard)
    assert rCutHard > 1.999, "hard redius cuttof cannot be lower than 1 Ang. rCut={}".format(rCutHard)
    assert nMax >= 2, "number of basis functions cannot be lower than 2. nMax={}".format(nMax)
    assert nMax <= 13, "number of basis functions cannot exceed 12. nMax={}".format(nMax)
    assert eta >= 0.0001, "Eta cannot be zero or negative. nMax={}".format(eta)

    # get clusgeo internal format for c-code
    Apos, typeNs, py_Ntypes, atomtype_lst, totalAN = _format_ase2clusgeo(obj, all_atomtypes)
    Hpos = np.array(Hpos)
    py_Hsize = Hpos.shape[0]

    # flatten arrays
    Hpos = Hpos.flatten()
    alp = alp.flatten()
    bet = bet.flatten()

    # convert int to c_int
    lMax = c_int(Lmax)
    Hsize = c_int(py_Hsize)
    Ntypes = c_int(py_Ntypes)
    totalAN = c_int(totalAN)
    rCutHard = c_double(rCutHard)
    Nsize = c_int(nMax)
    c_eta = c_double(eta)
    #convert int array to c_int array
    typeNs = (c_int * len(typeNs))(*typeNs)
    # convert to c_double arrays
    # alphas
    alphas = (c_double * len(alp))(*alp.tolist())
    # betas
    betas = (c_double * len(bet))(*bet.tolist())
    #Apos
    axyz = (c_double * len(Apos))(*Apos.tolist())
    #Hpos
    hxyz = (c_double * len(Hpos))(*Hpos.tolist())
    ### START SOAP###
    _PATH_TO_SOAPLITE_SO = os.path.dirname(os.path.abspath(__file__))
    _SOAPLITE_SOFILES = glob.glob( "".join([ _PATH_TO_SOAPLITE_SO, "/../libsoap/libsoap*.*so"]) ) ## NOT SURE ABOUT THIS

    if py_Ntypes == 1 or (not crossOver):
        substring = "libsoap/libsoapPySig."
        libsoap = CDLL(next((s for s in _SOAPLITE_SOFILES if substring in s), None))
        libsoap.soap.argtypes = [POINTER (c_double),POINTER (c_double), POINTER (c_double),POINTER (c_double), POINTER (c_double), POINTER (c_int),c_double,c_int,c_int,c_int,c_int,c_int,c_double]
        libsoap.soap.restype = POINTER (c_double)
        c = (c_double*(int((nMax*(nMax+1))/2)*(Lmax+1)*py_Ntypes*py_Hsize))()
        libsoap.soap( c, axyz, hxyz, alphas, betas, typeNs, rCutHard, totalAN, Ntypes, Nsize, lMax, Hsize,c_eta)
    else:
        substring = "libsoap/libsoapGTO."
        libsoapGTO = CDLL(next((s for s in _SOAPLITE_SOFILES if substring in s), None))
        libsoapGTO.soap.argtypes = [POINTER (c_double),POINTER (c_double), POINTER (c_double),POINTER (c_double), POINTER (c_double), POINTER (c_int),c_double,c_int,c_int,c_int,c_int,c_int,c_double]
        libsoapGTO.soap.restype = POINTER (c_double)
        c = (c_double*(int((nMax*(nMax+1))/2)*(Lmax+1)*int((py_Ntypes*(py_Ntypes +1))/2)*py_Hsize))()
        libsoapGTO.soap(c, axyz, hxyz, alphas, betas, typeNs, rCutHard, totalAN, Ntypes, Nsize, lMax, Hsize,c_eta)

    #   return c;
    if crossOver:
        crosTypes = int((py_Ntypes*(py_Ntypes+1))/2)
        shape = (py_Hsize, int((nMax*(nMax+1))/2)*(Lmax+1)*crosTypes)
    else:
        shape = (py_Hsize, int((nMax*(nMax+1))/2)*(Lmax+1)*py_Ntypes)

    a = np.ctypeslib.as_array(c)
    a = a.reshape(shape)

    return a


def get_soap_structure_gto(obj, alp, bet, rcut=5.0, nMax=5, Lmax=5, crossOver=True, all_atomtypes=None, eta=1.0):
    """Get the RBF basis SOAP output for atoms in a finite structure.

    Args:
        obj(ase.Atoms): Atomic structure for which the SOAP output is
            calculated.
        alp: Alphas
        bet: Betas
        rCut: Radial cutoff.
        nMax: Maximum nmber of radial basis functions
        Lmax: Maximum spherical harmonics degree
        crossOver:
        all_atomtypes: Can be used to specify the atomic elements for which to
            calculate the output. If given the output is calculated only for the
            given species.
        eta: The gaussian smearing width.

    Returns:
        np.ndarray: SOAP output for the given structure.
    """
    Hpos = obj.get_positions()
    arrsoap = get_soap_locals_gto(obj, Hpos, alp, bet, rcut, nMax, Lmax, crossOver, all_atomtypes=all_atomtypes, eta=eta)

    return arrsoap


def get_periodic_soap_locals_gto(system, positions, alp, bet, rcut=5.0, nMax=5, Lmax=5, crossOver=True, all_atomtypes=None, eta=1.0):
    """Get the RBF basis SOAP output for the given position in a periodic system.

    Args:
        obj(ase.Atoms): Atomic structure for which the SOAP output is
            calculated.
        alp: Alphas
        bet: Betas
        rcut: Radial cutoff.
        nMax: Maximum nmber of radial basis functions
        Lmax: Maximum spherical harmonics degree
        crossOver:
        all_atomtypes: Can be used to specify the atomic elements for which to
            calculate the output. If given the output is calculated only for the
            given species.
        eta: The gaussian smearing width.

    Returns:
        np.ndarray: SOAP output for the given position.
    """
    # The radial cutoff is determined by the rcut + the gaussian width that
    # extends the influence of atoms. We consider that three sigmas is
    # enough to make the gaussian decay.
    sigma = math.sqrt(1.0/(2*eta))
    radial_cutoff = rcut+3*sigma
    extended_system = get_extended_system(system, radial_cutoff, return_cell_indices=False)
    arrsoap = get_soap_locals_gto(extended_system, positions, alp, bet, rcut, nMax=nMax, Lmax=Lmax, crossOver=crossOver, all_atomtypes=all_atomtypes, eta=eta)

    return arrsoap


def get_periodic_soap_structure_gto(system, alp, bet, rcut=5.0, nMax=5, Lmax=5, crossOver=True, all_atomtypes=None, eta=1.0):
    """Get the RBF basis SOAP output for atoms in the given periodic system.

    Args:
        obj(ase.Atoms): Atomic structure for which the SOAP output is
            calculated.
        alp: Alphas
        bet: Betas
        rcut: Radial cutoff.
        nMax: Maximum nmber of radial basis functions
        Lmax: Maximum spherical harmonics degree
        crossOver:
        all_atomtypes: Can be used to specify the atomic elements for which to
            calculate the output. If given the output is calculated only for the
            given species.
        eta: The gaussian smearing width.

    Returns:
        np.ndarray: SOAP output for the given system.
    """
    positions = system.get_positions()

    # The radial cutoff is determined by the rcut + the gaussian width that
    # extends the influence of atoms. We consider that three sigmas is
    # enough to make the gaussian decay.
    sigma = math.sqrt(1.0/(2*eta))
    radial_cutoff = rcut+3*sigma
    extended_system = get_extended_system(system, radial_cutoff, return_cell_indices=False)
    arrsoap = get_soap_locals_gto(extended_system, positions, alp, bet, rcut, nMax, Lmax, crossOver, all_atomtypes=all_atomtypes, eta=eta)

    return arrsoap


def get_soap_locals_poly(obj, Hpos, rcut=5.0, nMax=5, Lmax=5, all_atomtypes=None, eta=1.0):
    rCutHard = rcut + 5
    nMax, rx, gss = get_basis_poly(rcut, nMax)

    assert Lmax <= 20, "l cannot exceed 20. Lmax={}".format(Lmax)
    assert Lmax >= 0, "l cannot be negative. Lmax={}".format(Lmax)
    assert rCutHard < 17.0001, "hard radius cuttof cannot be larger than 17 Angs. rcut={}".format(rCutHard)
    assert rCutHard > 1.9999, "hard radius cuttof cannot be lower than 1 Ang. rcut={}".format(rCutHard)
    # get clusgeo internal format for c-code
    Apos, typeNs, py_Ntypes, atomtype_lst, totalAN = _format_ase2clusgeo(obj, all_atomtypes)
    Hpos = np.array(Hpos)
    py_Hsize = Hpos.shape[0]

    # flatten arrays
    Hpos = Hpos.flatten()
    gss = gss.flatten()

    # convert int to c_int
    lMax = c_int(Lmax)
    Hsize = c_int(py_Hsize)
    Ntypes = c_int(py_Ntypes)
    totalAN = c_int(totalAN)
    rCutHard = c_double(rCutHard)
    Nsize = c_int(nMax)

    # convert double to c_double
    c_eta = c_double(eta)

    #convert int array to c_int array
    typeNs = (c_int * len(typeNs))(*typeNs)

    #Apos
    axyz = (c_double * len(Apos))(*Apos.tolist())
    #Hpos
    hxyz = (c_double * len(Hpos))(*Hpos.tolist())
    rx = (c_double * 100)(*rx.tolist())
    gss = (c_double * (100 * nMax))(*gss.tolist())

    ### START SOAP###
    _PATH_TO_SOAPLITE_SO = os.path.dirname(os.path.abspath(__file__))
    _SOAPLITE_SOFILES = glob.glob( "".join([ _PATH_TO_SOAPLITE_SO, "/../libsoap/libsoapG*.*so"]) )
    substring = "libsoap/libsoapGeneral."
    libsoap = CDLL(next((s for s in _SOAPLITE_SOFILES if substring in s), None))
    libsoap.soap.argtypes = [POINTER (c_double),POINTER (c_double), POINTER (c_double),
            POINTER (c_int), c_double,
            c_int,c_int,c_int,c_int,c_int,
            c_double, POINTER (c_double),POINTER (c_double)]
    libsoap.soap.restype = POINTER (c_double)

    c = (c_double*(int((nMax*(nMax+1))/2)*(Lmax+1)*int((py_Ntypes*(py_Ntypes+1))/2)*py_Hsize))()
    libsoap.soap(c, axyz, hxyz, typeNs, rCutHard, totalAN, Ntypes, Nsize, lMax, Hsize, c_eta, rx, gss)

    shape = (py_Hsize, int((nMax*(nMax+1))/2)*(Lmax+1)*int((py_Ntypes*(py_Ntypes+1))/2))
    crosTypes = int((py_Ntypes*(py_Ntypes+1))/2)
    shape = (py_Hsize, int((nMax*(nMax+1))/2)*(Lmax+1)*crosTypes)
    a = np.ctypeslib.as_array(c)
    a = a.reshape(shape)
    return a


def get_soap_structure_poly(obj, rcut=5.0, nMax=5, Lmax=5, all_atomtypes=None, eta=1.0):
    Hpos = obj.get_positions()
    arrsoap = get_soap_locals_poly(obj, Hpos, rcut, nMax, Lmax, all_atomtypes=all_atomtypes, eta=eta)

    return arrsoap


def get_periodic_soap_locals_poly(system, positions, rcut=5.0, nMax=5, Lmax=5, all_atomtypes=None, eta=1.0):
    # The radial cutoff is determined by the rcut + the gaussian width that
    # extends the influence of atoms. We consider that three sigmas is
    # enough to make the gaussian decay.
    sigma = math.sqrt(1.0/(2*eta))
    radial_cutoff = rcut+3*sigma
    extended_system = get_extended_system(system, radial_cutoff, return_cell_indices=False)
    arrsoap = get_soap_locals_poly(extended_system, positions, rcut, nMax, Lmax, all_atomtypes=all_atomtypes, eta=eta)

    return arrsoap


def get_periodic_soap_structure_poly(system, rcut=5.0, nMax=5, Lmax=5, all_atomtypes=None, eta=1.0):
    positions = system.get_positions()

    # The radial cutoff is determined by the rcut + the gaussian width that
    # extends the influence of atoms. We consider that three sigmas is
    # enough to make the gaussian decay.
    sigma = math.sqrt(1.0/(2*eta))
    radial_cutoff = rcut+3*sigma
    extended_system = get_extended_system(system, radial_cutoff, return_cell_indices=False)
    arrsoap = get_soap_locals_poly(extended_system, positions, rcut, nMax, Lmax, all_atomtypes=all_atomtypes, eta=eta)

    return arrsoap


def get_basis_gto(rcut, nmax):
    """Used to calculate the alpha and beta prefactors for the gto-radial
    basis.

    Args:
        rcut(float): Radial cutoff.
        nmax(int): Number of gto radial bases.

    Returns:
        (np.ndarray, np.ndarray): The alpha and beta prefactors for all bases
        up to a fixed size of l=10.
    """
    # These are the values for where the different basis functions should decay
    # to: evenly space between 1 angstrom and rcut.
    a = np.linspace(1, rcut, nmax)
    threshold = 1e-3  # This is the fixed gaussian decay threshold

    alphas_full = np.zeros((10, nmax))
    betas_full = np.zeros((10, nmax, nmax))

    for l in range(0, 10):
        # The alphas are calculated so that the GTOs will decay to the set
        # threshold value at their respective cutoffs
        alphas = -np.log(threshold/np.power(a, l))/a**2

        # Calculate the overlap matrix
        m = np.zeros((alphas.shape[0], alphas.shape[0]))
        m[:, :] = alphas
        m = m + m.transpose()
        S = 0.5*gamma(l + 3.0/2.0)*m**(-l-3.0/2.0)

        # Get the beta factors that orthonormalize the set with Löwdin
        # orthonormalization
        betas = sqrtm(inv(S))

        alphas_full[l, :] = alphas
        betas_full[l, :, :] = betas

    return alphas_full, betas_full


def get_basis_poly(rcut, nmax):
    """Used to calculate discrete vectors for the polynomial basis functions.

    Args:
        rcut(float): Radial cutoff.
        nmax(int): Number of polynomial radial bases.
    """
    # Calculate the overlap of the different polynomial functions in a
    # matrix S. These overlaps defined through the dot product over the
    # radial coordinate are analytically calculable: Integrate[(rc - r)^(a
    # + 2) (rc - r)^(b + 2) r^2, {r, 0, rc}]. Then the weights B that make
    # the basis orthonormal are given by B=S^{-1/2}
    S = np.zeros((nmax, nmax))
    for i in range(1, nmax+1):
        for j in range(1, nmax+1):
            S[i-1, j-1] = (2*(rcut)**(7+i+j))/((5+i+j)*(6+i+j)*(7+i+j))

    # Get the beta factors that orthonormalize the set with Löwdin
    # orthonormalization
    betas = sqrtm(np.linalg.inv(S))

    # If the result is complex, the calculation is currently halted.
    if (betas.dtype == np.complex128):
        raise ValueError(
            "Could not calculate normalization factors for the polynomial basis"
            " in the domain of real numbers. Lowering the number of radial "
            "basis functions is advised."
        )

    # It seems that the radial basis is integrated in a very specific
    # nonlinearly spaced grid given by rx
    x = np.zeros(100)
    x[0] = -0.999713726773441234
    x[1] = -0.998491950639595818
    x[2] = -0.996295134733125149
    x[3] = -0.99312493703744346
    x[4] = -0.98898439524299175
    x[5] = -0.98387754070605702
    x[6] = -0.97780935848691829
    x[7] = -0.97078577576370633
    x[8] = -0.962813654255815527
    x[9] = -0.95390078292549174
    x[10] = -0.94405587013625598
    x[11] = -0.933288535043079546
    x[12] = -0.921609298145333953
    x[13] = -0.90902957098252969
    x[14] = -0.895561644970726987
    x[15] = -0.881218679385018416
    x[16] = -0.86601468849716462
    x[17] = -0.849964527879591284
    x[18] = -0.833083879888400824
    x[19] = -0.815389238339176254
    x[20] = -0.79689789239031448
    x[21] = -0.77762790964949548
    x[22] = -0.757598118519707176
    x[23] = -0.736828089802020706
    x[24] = -0.715338117573056447
    x[25] = -0.69314919935580197
    x[26] = -0.670283015603141016
    x[27] = -0.64676190851412928
    x[28] = -0.622608860203707772
    x[29] = -0.59784747024717872
    x[30] = -0.57250193262138119
    x[31] = -0.546597012065094168
    x[32] = -0.520158019881763057
    x[33] = -0.493210789208190934
    x[34] = -0.465781649773358042
    x[35] = -0.437897402172031513
    x[36] = -0.409585291678301543
    x[37] = -0.380872981624629957
    x[38] = -0.351788526372421721
    x[39] = -0.322360343900529152
    x[40] = -0.292617188038471965
    x[41] = -0.26258812037150348
    x[42] = -0.23230248184497397
    x[43] = -0.201789864095735997
    x[44] = -0.171080080538603275
    x[45] = -0.140203137236113973
    x[46] = -0.109189203580061115
    x[47] = -0.0780685828134366367
    x[48] = -0.046871682421591632
    x[49] = -0.015628984421543083
    x[50] = 0.0156289844215430829
    x[51] = 0.046871682421591632
    x[52] = 0.078068582813436637
    x[53] = 0.109189203580061115
    x[54] = 0.140203137236113973
    x[55] = 0.171080080538603275
    x[56] = 0.201789864095735997
    x[57] = 0.23230248184497397
    x[58] = 0.262588120371503479
    x[59] = 0.292617188038471965
    x[60] = 0.322360343900529152
    x[61] = 0.351788526372421721
    x[62] = 0.380872981624629957
    x[63] = 0.409585291678301543
    x[64] = 0.437897402172031513
    x[65] = 0.465781649773358042
    x[66] = 0.49321078920819093
    x[67] = 0.520158019881763057
    x[68] = 0.546597012065094168
    x[69] = 0.572501932621381191
    x[70] = 0.59784747024717872
    x[71] = 0.622608860203707772
    x[72] = 0.64676190851412928
    x[73] = 0.670283015603141016
    x[74] = 0.693149199355801966
    x[75] = 0.715338117573056447
    x[76] = 0.736828089802020706
    x[77] = 0.75759811851970718
    x[78] = 0.77762790964949548
    x[79] = 0.79689789239031448
    x[80] = 0.81538923833917625
    x[81] = 0.833083879888400824
    x[82] = 0.849964527879591284
    x[83] = 0.866014688497164623
    x[84] = 0.881218679385018416
    x[85] = 0.89556164497072699
    x[86] = 0.90902957098252969
    x[87] = 0.921609298145333953
    x[88] = 0.933288535043079546
    x[89] = 0.94405587013625598
    x[90] = 0.953900782925491743
    x[91] = 0.96281365425581553
    x[92] = 0.970785775763706332
    x[93] = 0.977809358486918289
    x[94] = 0.983877540706057016
    x[95] = 0.98898439524299175
    x[96] = 0.99312493703744346
    x[97] = 0.99629513473312515
    x[98] = 0.998491950639595818
    x[99] = 0.99971372677344123

    rCutVeryHard = rcut+5.0
    rx = rCutVeryHard*0.5*(x + 1)

    fs = np.zeros([nmax, len(x)])
    for n in range(1, nmax+1):
        fs[n-1, :] = (rcut-np.clip(rx, 0, rcut))**(n+2)

    gss = np.dot(betas, fs)

    return nmax, rx, gss

import numpy as np


def get_asso_func(T_u, S, theta, asso_functions, n_long_features,
                  fixed_effect_time_order, derivative=False):
    """Computes association functions or derivatives association ones

    Parameters
    ----------
    T_u : `np.ndarray`, shape=(J,)
        The J unique censored times of the event of interest

    S : `np.ndarray`, shape=(2*N, r)
        Set of constructed Monte Carlo samples

    theta : `dict`
        Vector that concatenates all parameters to be inferred in the lights
        model

    asso_functions : `list` or `str`='all'
        List of association functions wanted or string 'all' to select all
        defined association functions. The available functions are :
            - 'lp' : linear predictor
            - 're' : random effects
            - 'tps' : time dependent slope
            - 'ce' : cumulative effects

    n_long_features : `int`
        Number of longitudinal features

    fixed_effect_time_order :
        Order of the higher time monomial considered for the representations of
        the time-varying features corresponding to the fixed effect. The
        dimension of the corresponding design matrix is then equal to
        fixed_effect_time_order + 1

    derivative : `bool`, default=False
    If `False`, returns the association functions, otherwise returns the
    derivative versions

    Returns
    -------
    asso_func_stack : `np.ndarray`, , shape=(2, n_samples*2*N, dim)
        Stack version of association functions or derivatives for all
        subjects, all groups and all Monte Carlo samples. `dim` is the
        total dimension of returned association functions.
    """
    fixed_effect_coeffs = np.array([theta["beta_0"],
                                    theta["beta_1"]])
    J = T_u.shape[0]
    q_l = fixed_effect_time_order + 1

    N = S.shape[0] // 2
    asso_func = AssociationFunctions(T_u, S, fixed_effect_coeffs,
                                     fixed_effect_time_order,
                                     n_long_features)

    if derivative:
        asso_func_stack = np.empty(shape=(2, 2 * N, J, n_long_features, 0))
    else:
        asso_func_stack = np.empty(shape=(2, J * 2 * N, 0))

    for func_name in asso_functions:
        if derivative:
            func = asso_func.assoc_func_dict["d_" + func_name]
            func_r = func.reshape(2, 2 * N, J, n_long_features, q_l)
        else:
            func = asso_func.assoc_func_dict[func_name]
            dim = n_long_features
            if func_name == 're':
                dim *= 2
            func_r = func.swapaxes(0, 1).swapaxes(2, 3).reshape(
                2, J * 2 * N, dim)
        asso_func_stack = np.concatenate((asso_func_stack, func_r), axis=-1)

    return asso_func_stack


class AssociationFunctions:
    """A class to define all the association functions

    Parameters
    ----------
    T : `np.ndarray`, shape=(n_samples,)
        Censored times of the event of interest

    S : `np.ndarray`, shape=(2*N, r)
        Set of samples used for Monte Carlo approximation

    fixed_effect_coeffs : `np.ndarray`,
        shape=((fixed_effect_time_order+1)*n_long_features,)
        Fixed effect coefficient vectors

    fixed_effect_time_order: `int`, default=5
        Order of the higher time monomial considered for the representations of
        the time-varying features corresponding to the fixed effect. The
        dimension of the corresponding design matrix is then equal to
        fixed_effect_time_order + 1

    n_long_features: `int`, default=5
        Number of longitudinal features
    """
    def __init__(self, T, S, fixed_effect_coeffs, fixed_effect_time_order=5,
                 n_long_features=5):
        self.S = S
        self.fixed_effect_coeffs = fixed_effect_coeffs
        self.n_long_features = n_long_features
        n_samples = len(T)
        self.n_samples = n_samples
        self.N = len(S) // 2
        self.r_l = 2  # linear time-varying features, so all r_l=2
        self.q_l = fixed_effect_time_order + 1

        U_l = np.ones(n_samples)
        # integral over U
        iU_l = T
        # derivative of U
        dU_l = np.zeros(n_samples)
        for t in range(1, self.q_l):
            U_l = np.c_[U_l, T ** t]
            iU_l = np.c_[iU_l, (T ** (t + 1)) / (t + 1)]
            dU_l = np.c_[dU_l, t * T ** (t - 1)]

        V_l = np.c_[np.ones(n_samples), T]
        iV_l = np.c_[T, (T ** 2) / 2]
        dV_l = np.c_[np.zeros(n_samples), np.ones(n_samples)]

        self.U_l, self.iU_l, self.dU_l = U_l, iU_l, dU_l
        self.V_l, self.iV_l, self.dV_l = V_l, iV_l, dV_l

        self.assoc_func_dict = {"lp": self.linear_predictor(),
                                "re": self.random_effects(),
                                "tps": self.time_dependent_slope(),
                                "ce": self.cumulative_effects(),
                                "d_lp": self.derivative_linear_predictor(),
                                "d_re": self.derivative_random_effects(),
                                "d_tps": self.derivative_time_dependent_slope(),
                                "d_ce": self.derivative_cumulative_effects()
                                }

    def _linear_association(self, U, V):
        """ Computes the linear association function U*beta + V*b

        Parameters
        ----------
        U : `np.ndarray`, shape=(n_samples, q_l)
            Fixed-effect design features

        V : `np.ndarray`, , shape=(n_samples, r_l)
            Random-effect design features

        Returns
        -------
        phi : `np.ndarray`, shape=(n_samples, 2, n_long_features, 2*N)
            The value of linear association function

        """
        beta = self.fixed_effect_coeffs
        n_samples = self.n_samples
        n_long_features = self.n_long_features
        S, N, r_l, q_l = self.S, self.N, self.r_l, self.q_l
        phi = np.zeros(shape=(n_samples, 2, n_long_features, 2 * N))

        for l in range(n_long_features):
            tmp = V.dot(S[:, r_l * l: r_l * (l + 1)].T)
            beta_0l = beta[0, q_l * l: q_l * (l + 1)]
            beta_1l = beta[1, q_l * l: q_l * (l + 1)]
            phi[:, 0, l, :] = U.dot(beta_0l) + tmp
            phi[:, 1, l, :] = U.dot(beta_1l) + tmp

        return phi

    def linear_predictor(self):
        """Computes the linear predictor function

        Returns
        -------
        phi : `np.ndarray`, shape=(n_samples, 2, n_long_features, 2*N)
            The value of linear predictor function
        """
        U_l, V_l = self.U_l, self.V_l
        phi = self._linear_association(U_l, V_l)
        return phi

    def random_effects(self):
        """ Computes the random effects function

        Returns
        -------
        phi : `np.ndarray`, shape=(n_samples, 2, r_l*n_long_features, 2*N)
            The value of random effects function
        """
        n_samples = self.n_samples
        n_long_features = self.n_long_features
        S, N, r_l = self.S, self.N, self.r_l
        phi = np.broadcast_to(S.T, (n_samples, 2, r_l * n_long_features, 2 * N))
        return phi

    def time_dependent_slope(self):
        """Computes the time-dependent slope function

        Returns
        -------
        phi : `np.ndarray`, shape=(n_samples, 2, n_long_features, 2*N)
            The value of time-dependent slope function
        """
        dU_l, dV_l = self.dU_l, self.dV_l
        phi = self._linear_association(dU_l, dV_l)
        return phi

    def cumulative_effects(self):
        """Computes the cumulative effects function

        Returns
        -------
        phi : `np.ndarray`, shape=(n_samples, 2, n_long_features, 2*N)
            The value of cumulative effects function
        """
        iU_l, iV_l = self.iU_l, self.iV_l
        phi = self._linear_association(iU_l, iV_l)
        return phi

    def derivative_random_effects(self):
        """ Computes the derivative of the random effects function

        Returns
        -------
        d_phi : `np.ndarray`, shape=(n_long_features, 2, 2*N, n_samples, q_l)
            The value of the derivative of the random effects function
        """
        n_samples = self.n_samples
        n_long_features = self.n_long_features
        N, q_l = self.N, self.q_l
        d_phi = np.zeros(shape=(2, 2 * N, n_samples, n_long_features, q_l))
        return d_phi

    def _get_derivative(self, val):
        """Formats the derivative based on its value

        Parameters
        ----------
        val : `np.ndarray`
            Value of the derivative

        Returns
        -------
        d_phi : `np.ndarray`, shape=(n_long_features, 2, 2*N, n_samples, q_l)
            The derivative broadcasted to the right shape
        """
        n_long_features = self.n_long_features
        N, q_l = self.N, self.q_l
        U = np.broadcast_to(val, (n_long_features,) + val.shape).swapaxes(0, 1)
        d_phi = np.broadcast_to(U, (2, 2 * N) + U.shape)
        return d_phi

    def derivative_linear_predictor(self):
        """Computes the derivative of the linear predictor function

        Returns
        -------
        output : `np.ndarray`, shape=(n_long_features, 2, 2*N, n_samples, q_l)
            The value of derivative of the linear predictor function
        """
        return self._get_derivative(self.U_l)

    def derivative_time_dependent_slope(self):
        """Computes the derivative of the time-dependent slope function

        Returns
        -------
        output : `np.ndarray`, shape= (2, 2*N, n_samples, n_l, q_l)
            The value of the derivative of the time-dependent slope function
        """
        return self._get_derivative(self.dU_l)

    def derivative_cumulative_effects(self):
        """Computes the derivative of the cumulative effects function

        Returns
        -------
        output : `np.ndarray`, shape=(n_long_features, 2, 2*N, n_samples, q_l)
            The value of the derivative of the cumulative effects function
        """
        return self._get_derivative(self.iU_l)

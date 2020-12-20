# -*- coding: utf-8 -*-
# Author: Simon Bussy <simon.bussy@gmail.com>

import numpy as np
from lights.base.base import logistic_loss, get_xi_from_xi_ext
from lights.model.regularizations import ElasticNet


class MstepFunctions:
    """A class to define functions relative to the M-step of the QNMCEM

    Parameters
    ----------
    fit_intercept : `bool`
        If `True`, include an intercept in the model for the time independent
        features

    X : `np.ndarray`, shape=(n_samples, n_time_indep_features)
        The time-independent features matrix

    T : `np.ndarray`, shape=(n_samples,)
        The censored times of the event of interest

    delta : `np.ndarray`, shape=(n_samples,)
        The censoring indicator

    n_time_indep_features : `int`
        Number of time-independent features

    n_long_features : `int`
        Number of longitudinal features

    l_pen : `float`, default=0
        Level of penalization for the ElasticNet and the Sparse Group l1

    eta_elastic_net: `float`, default=0.1
        The ElasticNet mixing parameter, with 0 <= eta_elastic_net <= 1.
        For eta_elastic_net = 0 this is ridge (L2) regularization
        For eta_elastic_net = 1 this is lasso (L1) regularization
        For 0 < eta_elastic_net < 1, the regularization is a linear combination
        of L1 and L2
    """

    def __init__(self, fit_intercept, X, T, delta, n_long_features,
                 n_time_indep_features, l_pen, eta_elastic_net,
                 nb_asso_features, fixed_effect_time_order):
        self.fit_intercept = fit_intercept
        self.X, self.T, self.delta = X, T, delta
        self.n_long_features = n_long_features
        self.n_time_indep_features = n_time_indep_features
        n_samples = len(T)
        self.n_samples = n_samples
        self.nb_asso_features = nb_asso_features
        self.fixed_effect_time_order = fixed_effect_time_order
        self.ENet = ElasticNet(l_pen, eta_elastic_net)

    def P_pen_func(self, pi_est, xi_ext):
        """Computes the sub objective function P with penalty, to be minimized
        at each QNMCEM iteration using fmin_l_bfgs_b.

        Parameters
        ----------
        pi_est : `np.ndarray`, shape=(n_samples,)
            The estimated posterior probability of the latent class membership
            obtained by the E-step

        xi_ext : `np.ndarray`, shape=(2*n_time_indep_features,)
            The time-independent coefficient vector decomposed on positive and
            negative parts

        Returns
        -------
        output : `float`
            The value of the P sub objective to be minimized at each QNMCEM step
        """
        xi_0, xi = get_xi_from_xi_ext(xi_ext, self.fit_intercept)
        pen = self.ENet.pen(xi)
        P = self.P_func(pi_est, xi_ext)
        sub_obj = P + pen
        return sub_obj

    def P_func(self, pi_est, xi_ext):
        """Computes the function denoted P in the lights paper.

        Parameters
        ----------
        pi_est : `np.ndarray`, shape=(n_samples,)
            The estimated posterior probability of the latent class membership
            obtained by the E-step

        xi_ext : `np.ndarray`, shape=(2*n_time_indep_features,)
            The time-independent coefficient vector decomposed on positive and
            negative parts

        Returns
        -------
        P : `float`
            The value of the P sub objective
        """
        xi_0, xi = get_xi_from_xi_ext(xi_ext, self.fit_intercept)
        u = xi_0 + self.X.dot(xi)
        P = (pi_est * logistic_loss(u)).mean()
        return P

    def grad_P(self, pi_est, xi_ext):
        """Computes the gradient of the function P

        Parameters
        ----------
        pi_est : `np.ndarray`, shape=(n_samples,)
            The estimated posterior probability of the latent class membership
            obtained by the E-step

        xi_ext : `np.ndarray`, shape=(2*n_time_indep_features,)
            The time-independent coefficient vector decomposed on positive and
            negative parts

        Returns
        -------
        output : `np.ndarray`
            The value of the P sub objective gradient
        """
        fit_intercept = self.fit_intercept
        X, n_samples = self.X, self.n_samples
        xi_0, xi = get_xi_from_xi_ext(xi_ext, fit_intercept)
        u = xi_0 + X.dot(xi)
        if fit_intercept:
            X = np.concatenate((np.ones(n_samples).reshape(1, n_samples).T, X),
                               axis=1)
        grad = X * (pi_est * np.exp(-logistic_loss(-u))).reshape(-1, 1)
        grad = - grad.mean(axis=0)
        grad_sub_obj = np.concatenate([grad, -grad])
        return grad_sub_obj

    def grad_P_pen(self, pi_est, xi_ext):
        """Computes the gradient of the sub objective P with penalty

        Parameters
        ----------
        pi_est : `np.ndarray`, shape=(n_samples,)
            The estimated posterior probability of the latent class membership
            obtained by the E-step

        xi_ext : `np.ndarray`, shape=(2*n_time_indep_features,)
            The time-independent coefficient vector decomposed on positive and
            negative parts

        Returns
        -------
        output : `np.ndarray`
            The value of the P sub objective gradient
        """
        fit_intercept = self.fit_intercept
        n_time_indep_features = self.n_time_indep_features
        xi_0, xi = get_xi_from_xi_ext(xi_ext, fit_intercept)
        grad_pen = self.ENet.grad(xi)
        if fit_intercept:
            grad_pen = np.concatenate([[0], grad_pen[:n_time_indep_features],
                                       [0], grad_pen[n_time_indep_features:]])
        grad_P = self.grad_P(pi_est, xi_ext)
        return grad_P + grad_pen

    def R_func(self, beta_k, *args):
        """Computes the function denoted R in the lights paper

        Parameters
        ----------
        beta_k : `np.ndarray`, shape=(n_long_features * q_l,)
            Fixed effect parameters for group k

        Returns
        -------
        output : `float`
            The value of the R function
        """
        n_samples = self.n_samples
        delta = self.delta
        arg = args[0]
        baseline_val = arg["baseline_hazard"].values.flatten()
        ind_2 = arg["ind_2"] * 1
        group = arg["group"]
        beta_k = beta_k.reshape(-1, 1)
        E_g1 = arg["E_g1"](beta_k).T[group].T
        E_g2 = arg["E_g2"](beta_k).T[group].T
        E_g9 = arg["E_g9"](beta_k).T[group].T
        pi_est = arg["pi_est"][group]
        sub_obj = E_g2 * delta + E_g9 - (E_g1 * baseline_val * ind_2).sum(
            axis=1)
        sub_obj = (pi_est * sub_obj).sum()
        return -sub_obj / n_samples

    def grad_R(self, beta_k, *args):
        """Computes the gradient of the function R

        Parameters
        ----------
        beta_k : `np.ndarray`, shape=(n_long_features * q_l,)
            Fixed effect parameters for group k

        Returns
        -------
        output : `np.ndarray`
            The value of the R gradient
        """
        p, L = self.n_time_indep_features, self.n_long_features
        n_samples = self.n_samples
        q_l = self.fixed_effect_time_order + 1
        arg = args[0]
        baseline_val = arg["baseline_hazard"].values.flatten()
        ind_2 = arg["ind_2"] * 1
        group = arg["group"]
        beta_k = beta_k.reshape(-1, 1)
        E_g5 = arg["E_g5"](beta_k).T[group].T
        E_g6 = arg["E_g6"](beta_k).T[group].T
        E_gS = arg["E_gS"]
        pi_est = arg["pi_est"][group]
        extracted_features = arg["extracted_features"]
        phi = arg["phi"]
        gamma_k = arg["gamma"][group][p:].reshape(L, -1)
        # To match the dimension of the association func derivative over beta
        gamma_k = np.repeat(gamma_k, q_l, axis=1)

        tmp1 = (E_g5.T * self.delta).T - \
               (E_g6.T * (ind_2 * baseline_val).T).T.sum(axis=1)
        # Split and sum over each l-th beta
        tmp1 = (tmp1 * gamma_k).reshape(n_samples, L, -1, q_l).sum(axis=2)

        (U_list, V_list, y_list, N_list) = extracted_features[0]
        tmp2 = np.zeros((n_samples, L * q_l))
        for i in range(n_samples):
            U_i, V_i, n_i, y_i = U_list[i], V_list[i], N_list[i], y_list[i]
            y_i = y_i.flatten()
            Phi_i = [[phi[l, 0]] * n_i[l] for l in range(L)]
            Phi_i = np.diag(np.concatenate(Phi_i))
            tmp2[i] = U_i.T.dot(Phi_i.dot(y_i - U_i.dot(beta_k.flatten()) -
                                          V_i.dot(E_gS[i]))).flatten()

        grad = ((tmp1.reshape(n_samples, -1) + tmp2).T * pi_est).sum(axis=1)
        grad_sub_obj = np.concatenate([grad, -grad])
        return -grad_sub_obj / n_samples

    def Q_func(self, gamma_k, *args):
        """ Computes the function denoted Q in the lights paper.

        Parameters
        ----------
        gamma_k : `np.ndarray`, shape=(nb_asso_feat,)
            Association parameters for group k

        Returns
        -------
        output : `float`
            The value of the Q function
        """
        n_samples, delta = self.n_samples, self.delta
        arg = args[0]
        group = arg["group"]
        gamma_k = gamma_k.reshape(-1, 1)
        baseline_val = arg["baseline_hazard"].values.flatten()
        ind_1, ind_2 = arg["ind_1"] * 1, arg["ind_2"] * 1
        E_g1 = arg["E_g1"](gamma_k).T[group].T
        E_log_g1 = np.log(E_g1)
        pi_est = arg["pi_est"][group]
        sub_obj = (E_log_g1 * ind_1).sum(axis=1) * delta - \
                  (E_g1 * ind_2 * baseline_val).sum(axis=1)
        sub_obj = (pi_est * sub_obj).sum()
        return -sub_obj / n_samples

    def grad_Q(self, gamma_k, *args):
        """Computes the gradient of the function Q

        Parameters
        ----------
        gamma_k : `np.ndarray`, shape=(nb_asso_feat,)
            Association parameters for group k

        Returns
        -------
        output : `np.ndarray`
            The value of the Q gradient
        """
        p, L = self.n_time_indep_features, self.n_long_features
        nb_asso_features = self.nb_asso_features
        n_samples, delta = self.n_samples, self.delta
        arg = args[0]
        baseline_val = arg["baseline_hazard"].values.flatten()
        ind_1, ind_2 = arg["ind_1"] * 1, arg["ind_2"] * 1
        group = arg["group"]
        gamma_k = gamma_k.reshape(-1, 1)
        E_g1 = arg["E_g1"](gamma_k).T[group].T
        E_g8 = arg["E_g8"](gamma_k).T[group].T.swapaxes(0, 1)
        E_g7 = arg["E_g7"].T[group].T
        pi_est = arg["pi_est"][group]
        grad = np.zeros(nb_asso_features)
        grad[:p] = (self.X.T * (pi_est * (delta - (E_g1 * baseline_val * ind_2)
                                          .sum(axis=1)))).sum(axis=1)
        tmp = (E_g7.T * delta * ind_1.T).T.sum(axis=1) - (
                    E_g8.T * baseline_val * ind_2).sum(axis=-1).T
        grad[p:] = (tmp.swapaxes(0, 1) * pi_est).sum(axis=1)
        grad_sub_obj = np.concatenate([grad, -grad])
        return -grad_sub_obj / n_samples

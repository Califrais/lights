# -*- coding: utf-8 -*-
# Author: Simon Bussy <simon.bussy@gmail.com>

import numpy as np
import statsmodels.formula.api as smf
import pandas as pd


class ULMM:
    """Algorithm for fitting a univariate linear mixed model

    Parameters
    ----------
    fixed_effect_time_order : `int`, default=5
        Order of the higher time monomial considered for the representations of
        the time-varying features corresponding to the fixed effect. The
        dimension of the corresponding design matrix is then equal to
        fixed_effect_time_order + 1
    """

    def __init__(self, fixed_effect_time_order=5):
        self.fixed_effect_time_order = fixed_effect_time_order

        # Attributes that will be instantiated afterwards
        self.beta = None
        self.D = None
        self.phi = None

    def fit(self, extracted_features):
        """Fit univariate linear mixed models

        Parameters
        ----------
        extracted_features : `tuple, tuple`,
            The extracted features from longitudinal data.
            Each tuple is a combination of fixed-effect design features,
            random-effect design features, outcomes, number of the longitudinal
            measurements for all subject or arranged by l-th order.
        """
        fixed_effect_time_order = self.fixed_effect_time_order
        q_l = fixed_effect_time_order + 1
        r_l = 2  # linear time-varying features, so all r_l=2
        (U_list, V_list, y_list, N), (U_L, V_L, y_L, N_L) = extracted_features
        n_samples, n_long_features = len(U_list), len(U_L)
        q = q_l * n_long_features
        r = r_l * n_long_features

        beta = np.zeros(q)
        D = np.zeros((r, r))
        phi = np.ones(n_long_features)

        for l in range(n_long_features):
            U = U_L[l][:, 1:]
            V = U_L[l][:, 1:r_l]
            Y = y_L[l]
            S = np.array([])
            for i in range(n_samples):
                S = np.append(S, i * np.ones(N_L[l][i]))

            fixed_effect_columns = []
            other_columns = ['V', 'Y', 'S']
            for j in range(fixed_effect_time_order):
                fixed_effect_columns.append('U' + str(j + 1))
            data = pd.DataFrame(data=np.hstack((U, V, Y, S.reshape(-1, 1))),
                                columns=fixed_effect_columns + other_columns)

            md = smf.mixedlm("Y ~ " + ' + '.join(fixed_effect_columns), data,
                             groups=data["S"], re_formula="~V")
            mdf = md.fit()
            beta[q_l * l] = mdf.params["Intercept"]
            beta[q_l * l + 1: q_l * (l + 1)] = [mdf.params[features]
                                                for features in
                                                fixed_effect_columns]

            D[r_l * l: r_l * (l + 1), r_l * l: r_l * (l + 1)] = np.array(
                [[mdf.params["Group Var"], mdf.params["Group x V Cov"]],
                 [mdf.params["Group x V Cov"], mdf.params["V Var"]]])
            phi[l] = mdf.resid.values.var()

        self.beta = beta.reshape(-1, 1)
        self.D = D
        self.phi = phi.reshape(-1, 1)
import numpy as np
from numpy import linalg as LA
from numpy.linalg import multi_dot
import cv2
import sys
import pickle


def prox_tnn(Y, rho):
    n1, n2, n3 = Y.shape
    X = np.zeros((n1, n2, n3), dtype=complex)
    Y = np.fft.fft(Y)
    tnn = 0
    trank = 0
    U, S, V = np.linalg.svd(Y[:, :, 0], full_matrices=False)
    r = np.sum(S > rho)
    if r >= 1:
        S = S[:r] - rho
        X[:, :, 0] = multi_dot([U[:, :r], np.diag(S), V[:r, :]])
        tnn += np.sum(S)
        trank = max(trank, r)
    halfn3 = round(n3/2)
    for i in range(1, halfn3):
        U, S, V = np.linalg.svd(Y[:, :, i], full_matrices=False)
        r = np.sum(S > rho)
        if r >= 1:
            S = S[:r] - rho
            X[:, :, i] = multi_dot([U[:, :r], np.diag(S), V[:r, :]])
            tnn += np.sum(S)*2
            trank = max(trank, r)
        X[:, :, n3 - i] = np.conjugate(X[:, :, i])
    if n3 % 2 == 0:
        i = halfn3
        U, S, V = np.linalg.svd(Y[:, :, i], full_matrices=False)
        r = np.sum(S > rho)
        if r >= 1:
            S = S[:r] - rho
            X[:, :, i] = multi_dot([U[:, :r], np.diag(S), V[:r, :]])
            tnn += np.sum(S)
            trank = max(trank, r)
    tnn /= 3
    X = np.fft.ifft(X)
    return X, tnn, trank


def prox_l1(b, plambda):
    return np.maximum(0, b - plambda) + np.minimum(0, b + plambda)


def trpca(X, plambda, tol=1e-8, max_iter=500, rho=1.1, mu=1e-4, max_mu=1e10):
    L = np.zeros(X.shape)
    S = L
    Y = L
    for i in range(max_iter):
        Lk = L
        Sk = S
        L, tnnL, _ = prox_tnn(-S + X - Y / mu, 1 / mu)
        S = prox_l1(-L + X - Y / mu, plambda / mu)
        dY = L + S - X
        chgL = np.max(abs(Lk - L))
        chgS = np.max(abs(Sk - S))
        chg = max(chgL, chgS, np.max(abs(dY)))
        if chg < tol:
            break
        Y = Y + mu * dY
        mu = min(rho * mu, max_mu)
        obj = tnnL + plambda * LA.norm(S.flatten(), ord=1)
        err = LA.norm(dY.flatten(), ord=2)
        print("Iter: %d/%d     Err: %.4f" % (i + 1, max_iter, err))
    return L, S, obj, err, i


def frame_capture(path):
    vidObj = cv2.VideoCapture(path)
    count = 0
    success = 1
    while True:
        success, image = vidObj.read()
        if not success:
            break
#         image = image.astype("float64") / 255
        image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        # cv2.imwrite("./Dataset/Videos/italy_short/frame%d.jpg" %(count), image)
        if count == 0:
            X = np.array(image).astype("float64")[:, :, np.newaxis]
        else:
            X = np.concatenate((X, np.array(image).astype("float64")[:, :, np.newaxis]), axis=2)
        count += 1
    print("Frame extracted done!")
    return X


if __name__ == "__main__":
    inp_path = sys.argv[1];
    # oup_path1 = sys.argv[2];
    # oup_path2 = sys.argv[3];
    X = frame_capture(inp_path)
    X = X / 255
    maxP = np.max(abs(X))
    n1, n2, n3 = X.shape
    Xn = np.copy(X)
    rhos = 0.3

    # customize your own noise
    ind = np.zeros((n1, n2, n3), dtype=bool)
    ind = np.random.rand(n1, n2, n3) < rhos
    ind[0:100, :, :] = False
    ind[150:, :, :] = False  # 100:150, 200:250
    ind[:, 0:200, :] = False
    ind[:, 250:, :] = False
    Xn[ind] = np.random.rand(np.sum(ind))

    mu = 1e-4
    max_mu = 1e10
    tol = 1e-5
    rho = 1.1
    max_iter = 500
    n1, n2, n3 = Xn.shape
    plambda = 1 / np.sqrt(max(n1, n2) * n3)
    L, S, E, err, i = trpca(Xn, plambda, tol, max_iter, rho, mu, max_mu)
    Xhat = L
    Xhat = np.maximum(Xhat, 0)
    Xhat = np.minimum(Xhat, maxP)

    with open("./output_ori_trpca", 'wb') as f:
        pickle.dump(X, f)
    with open("./output_cor_trpca", 'wb') as f:
        pickle.dump(Xn, f)
    with open("./output_rec_trpca", 'wb') as f:
        pickle.dump(Xhat, f)

    print("Done!")
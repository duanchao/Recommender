# -*- coding: utf-8 -*-
from __future__ import unicode_literals
'''
Created on Sep 8, 2017

@author: ming



this method  defined that
u_bias: [ number_users ]
v_bias: [ number_items ]

two approach to solve this problem:
    1. close-form solution , Four parameters, and solute by gradient=0
    2. ALS approach by augmentation array only two parameters.

'''




import os,sys
import time
import logging
from util import adam,eval_RMSE_bias_alpha_beta
import math
import numpy as np
import pickle

def BiasMF(train_user, train_item, valid_user, test_user,
           R, max_iter=50, lambda_u=1, lambda_v=100, dimension=50,momentum_flag=1):
    # explicit setting
    a = 1
    b = 0

    eta=-0.001
    max_iter=200

    num_user = R.shape[0]
    num_item = R.shape[1]
    print "===================================ConvMF Models==================================="
    print "\tnum_user is:{}".format(num_user)
    print "\tnum_item is:{}".format(num_item)
    print "==================================================================================="
    PREV_LOSS = 1e-50

    Train_R_I = train_user[1] #this is rating; train_user_[0] is the item_index
    Train_R_J = train_item[1]
    Test_R = test_user[1]
    Valid_R = valid_user[1]


    '''
    compute the average of R
    '''

    train_sum=0
    test_sum=0#= np.sum(test_user[1])
    valid_sum=0#np.sum(valid_user[1])
    train_size=0#np.size(train_user[1])
    test_size=0# np.size(test_user[1])
    valid_size=0#np.size(valid_user[1])
    total_sum=0#train_sum+test_sum+valid_sum
    user_bias_sum=[]
    item_bias_sum=[]
    user_bias_size=[]
    item_bias_size=[]
    '''
    obtain the average rating of each user
    '''
    for item in train_user[1]:
        train_sum=train_sum+ np.sum(item)
        train_size=train_size+np.size(item)

        user_bias_sum.append(np.sum(item))
        user_bias_size.append(len(item))

    for item in test_user[1]:
        test_sum=test_sum+ np.sum(item)
        test_size=test_size+np.size(item)
    for item in valid_user[1]:
        valid_sum=valid_sum+ np.sum(item)
        valid_size=valid_size+np.size(item)

    total_size=train_size+test_size+valid_size
    total_sum=train_sum+test_sum+valid_sum
    global_average=total_sum*1.0/total_size
    user_bias=[user_bias_sum[i]/user_bias_size[i] for i in range(len(user_bias_sum))]




    print "######################################"
    print "sum: ",train_sum,test_sum,valid_sum
    print "size: ",train_size,test_size,valid_size
    print "average: ",train_sum*1.0/train_size, test_sum*1.0/test_size, valid_sum*1.0/valid_size
    print "global average: ",total_sum*1.0/total_size
    print "user_bias:",user_bias[0:10]
    print "######################################"



    pre_val_eval = 1e10
    V = np.random.uniform(0,1,size=(num_item,dimension))
    U = np.random.uniform(0,1,size=(num_user, dimension))
    Alpha =  np.random.uniform(0,1,size=(num_user))
    Beta  =  np.random.uniform(0,1,size=(num_item))

    print V[0,1:3]
    print U[0,1:3]
    endure_count = 100
    count = 0
    better_rmse =100.0
    better_mae = 100.0
    better_ndcg=0

    if momentum_flag== 0:
        '''
        first method by conventional method
        '''
        print "first conventional method"
        for iteration in xrange(max_iter):
            loss = 0
            tic = time.time()
            print "%d iteration\t(patience: %d)" % (iteration, count)
            sub_loss = np.zeros(num_user)
            print "=================================================================="
            print "the shape of U, U[i] {} {}".format(U.shape,U[0].shape)
            print "=================================================================="
            for i in xrange(num_user):
                idx_item = train_user[0][i]
                #train_user[0]=[[item1,item2,item3...],[item1,itme3],[item3,item2]...]
                #train_user[1]=[[rating1,rating2,rating3...],[rating1,rating3],[rating2,rating5]...]

                V_i = V[idx_item]
                R_i = Train_R_I[i]#[rating1,rating2,rating3...]

                alpha=np.ones([num_item])*Alpha[i]
                middle = R_i -Beta[idx_item] - alpha[idx_item]

                # close-form  solution
                A = V_i.T.dot(V_i) + lambda_u * np.eye(dimension)
                B = (a * V_i * (np.tile(middle, (dimension, 1)).T)).sum(0) #np.tile() array copy; sum(0) is the sum of each column,sum(1) is the sum of each row;
                U[i] = (np.linalg.solve(A.T, B.T)).T      #AX=B,X=A^(-1)B

                sub_loss[i] = -0.5 * lambda_u * np.dot(U[i], U[i])

                #update Alpha
                molecule=np.sum((R_i -U[i].dot(V_i.T))) -np.sum(Beta[idx_item])
                denominator = lambda_u+np.sum(len(idx_item))
                Alpha[i]=molecule/denominator



            loss = loss + np.sum(sub_loss) +np.sum(np.square(Alpha))

            print "=================================================================="
            print "the shape of V, V[i] {} {}".format(V.shape,V[0].shape)
            print "=================================================================="
            sub_loss = np.zeros(num_item)
            for j in xrange(num_item):
                idx_user = train_item[0][j]
                U_j = U[idx_user]
                R_j = Train_R_J[j]

                beta=np.ones([num_user])*Beta[j]
                middle = R_j -Alpha[idx_user] - beta[idx_user]


                A =  (U_j.T.dot(U_j)) +lambda_v * np.eye(dimension)
                B = (a * U_j * (np.tile(middle, (dimension, 1)).T)).sum(0)
                V[j] = (np.linalg.solve(A.T, B.T)).T #A*X=B  X =A^-1*B

                #alter the rating by bias
                RR_j = R_j -Alpha[idx_user] - Beta[j]


                sub_loss[j] = -0.5 * lambda_v * np.dot(V[j], V[j])
                sub_loss[j] = sub_loss[j]-0.5 * np.square(RR_j).sum()
                sub_loss[j] = sub_loss[j] + a * np.sum((U_j.dot(V[j])) * RR_j)
                sub_loss[j] = sub_loss[j] - 0.5 * np.dot(V[j].dot(A), V[j])

                #update Beta
                molecule=np.sum((R_j -U_j.dot(V[j].T))) -np.sum(Alpha[idx_user])
                denominator = lambda_v+np.sum(len(idx_user))
                Alpha[i]=molecule/denominator

            loss =(loss + np.sum(sub_loss))+ np.sum(np.square(beta))
            seed = np.random.randint(100000)



            topk=[3,5,10,15,20,25,30,40,50,100]
            tr_eval,tr_recall,tr_mae=eval_RMSE_bias_alpha_beta(Train_R_I, U, V, train_user[0],topk, Alpha,Beta, user_bias)
            val_eval,va_recall,va_mae = eval_RMSE_bias_alpha_beta(Valid_R, U, V, valid_user[0],topk,Alpha,Beta, user_bias)
            te_eval,te_recall,te_mae = eval_RMSE_bias_alpha_beta(Test_R, U, V, test_user[0],topk,Alpha,Beta, user_bias)


            for i in range(len(topk)):
                print "recall top-{}: Train:{} Validation:{}  Test:{}".format(topk[i],tr_recall[i],va_recall[i],te_recall[i])

            toc = time.time()
            elapsed = toc - tic
            converge = abs((loss - PREV_LOSS) / PREV_LOSS)

            if (val_eval < pre_val_eval):
                print "Best Test result!!!!!"
            else:
                count = count + 1

            pre_val_eval = val_eval

            print "=====================RMSE============================="
            print "Loss: %.5f Elpased: %.4fs Converge: %.6f Train: %.5f Validation: %.5f Test: %.5f" % (
            loss, elapsed, converge, tr_eval, val_eval, te_eval)
            print "=====================MAE============================="
            print " Train: %.5f Validation: %.5f Test: %.5f" % ( tr_mae, va_mae, te_mae)


            if te_eval <better_rmse:
                better_rmse=te_eval
            if te_mae < better_mae:
                better_mae = te_mae
            print "\n BiasMF========better_rmse:{}   better_mae:{}==========\n".format(better_rmse,better_mae)

            if (count == endure_count):
                break
            PREV_LOSS = loss


    else:
        '''
        second method by ALS approach, augmentation array

        step 1:
             rr_i,j = r_i,j - Beta[j]
             uu_i   = [Alpha[i],u_i]          1*(K+1) K is the dimension of latent factors
             vv_j   = [1, v_j]                1*(K+1)

             rr_i,j  = uu_i * vv_j^T= Alpha[i] + u_i*v_j^T

             and then we can obtain uu_i;
        step 2:
            rr_i,j = r_i,j - Alpha[i]
            uu_i   = [1,u_i]             1*(K+1) K is the dimension of latent factors
            vv_j   = [Beta[j], v_j]      1*(K+1)

            rr_i,j  = uu_i * vv_j^T= Beta[j] + u_i*v_j^T

            and then we can obtain  vv_j

        '''
        print "second method by augmentation array"


        for iteration in xrange(max_iter):

            loss = 0
            tic = time.time()
            print "%d iteration\t(patience: %d)" % (iteration, count)

            sub_loss = np.zeros(num_user)
            print "=================================================================="
            print "the shape of U, U[i] {} {}".format(U.shape,U[0].shape)
            print "=================================================================="


            '''
            step 1:
            rr_i,j = r_i,j - Beta[j]
            uu_i   = [Alpha[i],u_i]          1*(K+1) K is the dimension of latent factors
            vv_j   = [1, v_j]                1*(K+1)

            rr_i,j  = uu_i * vv_j^T= Alpha[i] + u_i*v_j^T

            and then we can obtain uu_i;
            '''

            VV = np.concatenate((np.ones((num_item,1)),V),axis=1)
            UU = np.concatenate((Alpha.reshape(Alpha.shape[0],1),U),axis=1)


            for i in xrange(num_user):
                idx_item = train_user[0][i]
                #train_user[0]=[[item1,item2,item3...],[item1,itme3],[item3,item2]...]
                #train_user[1]=[[rating1,rating2,rating3...],[rating1,rating3],[rating2,rating5]...]

                VV_i = VV[idx_item]
                RR_i = Train_R_I[i] - Beta[idx_item] #[rating1,rating2,rating3...]


                A = lambda_u * np.eye(dimension+1)+ (VV_i.T.dot(VV_i))
                B = (VV_i * (np.tile(RR_i, (dimension+1, 1)).T)).sum(0) #np.tile() array copy; sum(0) is the sum of each column,sum(1) is the sum of each row;
                UU[i] = (np.linalg.solve(A.T, B.T)).T      #AX=B,X=A^(-1)B
                sub_loss[i] = -0.5 * lambda_u * np.dot(U[i], U[i])

            loss = loss + np.sum(sub_loss)
            print "=================================================================="
            print "the shape of V, V[i] {} {}".format(V.shape,V[0].shape)
            print "=================================================================="
            sub_loss = np.zeros(num_item)

            U = UU[:,1:]
            Alpha=UU[:,0]


            '''
            step 2
            rr_i,j = r_i,j - Alpha[i]
            uu_i   = [1,u_i]             1*(K+1) K is the dimension of latent factors
            vv_j   = [Beta[j], v_j]      1*(K+1)

            rr_i,j  = uu_i * vv_j^T= Beta[j] + u_i*v_j^T

            and then we can obtain  vv_j
            '''
            UU = np.concatenate((np.ones((num_user,1)),U),axis=1)
            VV = np.concatenate((Beta.reshape(Beta.shape[0],1),V),axis=1)
            for j in xrange(num_item):
                idx_user = train_item[0][j]
                UU_j = UU[idx_user]
                RR_j = Train_R_J[j] - Alpha[idx_user]

                A = (UU_j.T.dot(UU_j))+lambda_v * np.eye(dimension+1)
                B = (UU_j * (np.tile(RR_j, (dimension+1, 1)).T)).sum(0)
                VV[j] = (np.linalg.solve(A.T, B.T)).T #A*X=B  X =A^-1*B

                sub_loss[j] = -0.5 * lambda_v * np.dot(VV[j], VV[j])
                sub_loss[j] = sub_loss[j]-0.5 * np.square(RR_j).sum()
                sub_loss[j] = sub_loss[j] +  np.sum((UU_j.dot(VV[j])) * RR_j)
                sub_loss[j] = sub_loss[j] - 0.5 * np.dot(VV[j].dot(A), VV[j])


            loss =(loss + np.sum(sub_loss))
            seed = np.random.randint(100000)

            V= VV[:,1:]
            Beta = VV[:,0]

            '''
            evaluate RMSE and  Recall@k
            '''
            topk=[3,5,10,15,20,25,30,40,50,100]

            tr_eval,tr_recall,tr_mae,tr_ndcg=eval_RMSE_bias_alpha_beta(Train_R_I, U, V, train_user[0],topk, Alpha,Beta, user_bias)
            val_eval,va_recall,va_mae,val_ndcg = eval_RMSE_bias_alpha_beta(Valid_R, U, V, valid_user[0],topk,Alpha,Beta, user_bias)
            te_eval,te_recall,te_mae,te_ndcg = eval_RMSE_bias_alpha_beta(Test_R, U, V, test_user[0],topk,Alpha,Beta, user_bias)

            for i in range(len(topk)):
                print "recall top-{}: Train:{} Validation:{}  Test:{}".format(topk[i],tr_recall[i],va_recall[i],te_recall[i])
            print "ndcg train {}, val {}, test {}".format(tr_ndcg,val_ndcg,te_ndcg)


            toc = time.time()
            elapsed = toc - tic
            converge = abs((loss - PREV_LOSS) / PREV_LOSS)

            if (val_eval < pre_val_eval):
                print "Best Test result!!!!!"
            else:
                count = count + 1

            pre_val_eval = val_eval

            print "=====================RMSE============================="
            print "Loss: %.5f Elpased: %.4fs Converge: %.6f Train: %.5f Validation: %.5f Test: %.5f" % (
            loss, elapsed, converge, tr_eval, val_eval, te_eval)
            print "=====================MAE============================="
            print " Train: %.5f Validation: %.5f Test: %.5f" % ( tr_mae, va_mae, te_mae)


            if te_eval <better_rmse:
                better_rmse=te_eval
            if te_mae < better_mae:
                better_mae = te_mae
            if te_ndcg[1] <better_ndcg:
                better_ndcg=te_ndcg[1]

            print "\n BiasMF========better_rmse:{}   better_mae:{}==========\n".format(better_rmse,better_mae)

            if (count == endure_count):
                break
            PREV_LOSS = loss





'''
Created on Sep 8, 2017

@author: ming
'''

import os
import time
import logging
from util import eval_RMSE,eval_RMSE_bais,recall_top
import util
import math
import numpy as np

from mlp_module.mlp import MLP_module
from mlp_module.double_mlp import Double_MLP_module

def Neural_Matrix_Factorization(res_dir, train_user, train_item, valid_user, test_user,
           R, CNN_X, vocab_size, init_W=None, give_item_weight=True,
           max_iter=50, lambda_u=1, lambda_v=100, dimension=50,
           dropout_rate=0.2, emb_dim=200, max_len=300, num_kernel_per_ws=100,lambda_type=1212):
    # explicit setting
   
    dimension=50
    num_class=1


    num_user = R.shape[0]
    num_item = R.shape[1]
    print "===================================ConvMF Models==================================="
    print "\tnum_user is:{}".format(num_user)
    print "\tnum_item is:{}".format(num_item)
    print "==================================================================================="
    PREV_LOSS = 1e-40
 

    Train_R_I = train_user[1] #this is rating; train_user_[0] is the item_index
    Train_R_J = train_item[1]
    Test_R = test_user[1]
    Valid_R = valid_user[1]

    pre_val_eval = 1e10


    endure_count = 100
    count = 0

    print "===================================numpy dot==================================="
    print np.dot.__module__
    print "==============================================================================="
    '''
    train_user[0]=[[item1,item2,item3...],[item1,itme3],[item3,item2]...]
    train_user[1]=[[rating1,rating2,rating3...],[rating1,rating3],[rating2,rating5]...]
    R_i = Train_R_I[i]#[rating1,rating2,rating3...]
    '''


    '''
    user bias
    '''
    user_bias_sum=[]
    user_bias_size=[]
    for item in train_user[1]:
        user_bias_sum.append(np.sum(item))
        user_bias_size.append(len(item))
    user_bias=[user_bias_sum[i]/user_bias_size[i] for i in range(len(user_bias_sum))]
    print "######################################"
    print "user_bias:",user_bias[0:10]
    print "######################################"

    '''
    input format:(u,v,r)
    '''
    def get_instance(data):
        input_u=[]
        input_v=[]
        input_r=[]
        for i in xrange(num_user):
            R_i = data[1][i]
            idx_item = data[0][i]
            # print len(R_i),len(idx_item)
            # print idx_item
            for j in range(len(idx_item)):
                input_u.append(i)
                input_v.append(idx_item[j])
                input_r.append((R_i[j]-1)/4.0)
        input_r=np.array(input_r)
        input_v=np.array(input_v)
        input_u=np.array(input_u)
        print "=================================="
        print  "the shape of input_u,input_v,input_r ",input_u.shape,input_v.shape,input_r.shape
        print "=================================="
        return input_u,input_v,input_r


    input_u,input_v,input_r=get_instance(train_user)

    v_input_u,v_input_v,v_input_r=get_instance(valid_user)
    t_input_u,t_input_v,t_input_r=get_instance(test_user)

    if lambda_type == 1212:
        model = Double_MLP_module(num_class,dimension,num_user,num_item,lambda_u,lambda_v)
    else:
        model=MLP_module(num_class,dimension,num_user,num_item,lambda_u,lambda_v)

    max_iter=100
    for iteration in xrange(max_iter):
        loss = 0
        tic = time.time()
        print "%d iteration\t(patience: %d)" % (iteration, count)
        seed = np.random.randint(10000)
        loss=model.train(input_u,input_v,input_r,seed)
        # print "loss of the train process for mlp is {}".format(loss)



        val_eval = model.predict(v_input_u,v_input_v,v_input_r)
        v_out=model.out_put_score

        te_eval = model.predict(t_input_u,t_input_v,t_input_r)
        t_out=model.out_put_score



        toc = time.time()
        elapsed = toc - tic
        converge = abs((loss - PREV_LOSS) / PREV_LOSS)
        if (val_eval < pre_val_eval):
            pass
        else:
            count = count + 1
        pre_val_eval = val_eval

        # print "origin Loss: %.5f Elpased: %.4fs Converge: %.6f Train: %.5f Validation: %.5f Test: %.5f" % (
        #     loss, elapsed, converge, tr_eval, val_eval, te_eval)


        topk=[3,5,10,15,20,25,30,40,50,100]
        val_eval,va_recall=recall_top(num_user, v_input_u,v_input_r,v_out,topk,user_bias)
        te_eval,te_recall = recall_top(num_user, t_input_u,t_input_r,t_out,topk,user_bias)

        for i in range(len(topk)):
            print "recall top-{}: Train, Validation:{}  Test:{}".format(topk[i],va_recall[i],te_recall[i])
        print "final Loss: %.5f Elpased: %.4fs Converge: %.6f Train: %.5f Validation: %.5f Test: %.5f" % (
            loss, elapsed, converge, loss, val_eval, te_eval)

     
        if (count == endure_count):
            break
        PREV_LOSS = loss


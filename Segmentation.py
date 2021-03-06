'''
Segmentation.py

The Segmentation module for DIRT. We perform connected component labeling and construct the medial axis graph here.

The code is free for non-commercial use.
Please contact the author for commercial use.

Please cite the DIRT Paper if you use the code for your scientific project.

Bucksch et al., 2014 "Image-based high-throughput field phenotyping of crop roots", Plant Physiology

-------------------------------------------------------------------------------------------
Author: Alexander Bucksch
School of Biology and Interactive computing
Georgia Institute of Technology

Mail: bucksch@gatech.edu
Web: http://www.bucksch.nl
-------------------------------------------------------------------------------------------

Copyright (c) 2014 Alexander Bucksch
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above
    copyright notice, this list of conditions and the following
    disclaimer in the documentation and/or other materials provided
    with the distribution.

  * Neither the name of the DIRT Developers nor the names of its
    contributors may be used to endorse or promote products derived
    from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

'''
# external library imports
'''
import numpy as np
from scipy import ndimage
import graph_tool.topology as gt
import graph_tool.util as gu
from graph_tool import Graph
import mahotas as m

'''
# standard python import
'''
import time

class Segmentation(object):
    '''
    classdocs
    '''
    def __init__(self,img,io=0,tips=[],):
        '''
        Constructor
        '''
        self.__idIdx=io.getCurrentID()
        self.__img = img
        self.__io = io
        self.__id = io.getID()
        self.__height, self.__width = np.shape(self.__img)
        self.__tips=tips
        self.__fail=False
    def getFail(self):
        return self.__fail
    def setTips(self,tips):
        '''
        BAD HACK. DO IT CLEAN IN THE REFACTORED VERSION
        '''
        self.__tips=tips
        
    def smooth(self,x,window_len=11,window='hanning'):
        """smooth the data using a window with requested size.
        
        This method is based on the convolution of a scaled window with the signal.
        The signal is prepared by introducing reflected copies of the signal 
        (with the window size) in both ends so that transient parts are minimized
        in the begining and end part of the output signal.
        
        input:
            x: the input signal 
            window_len: the dimension of the smoothing window; should be an odd integer
            window: the type of window from 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
                flat window will produce a moving average smoothing.
    
        output:
            the smoothed signal
            
        example:
    
        t=linspace(-2,2,0.1)
        x=sin(t)+randn(len(t))*0.1
        y=smooth(x)
        
        see also: 
        
        numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman, numpy.convolve
        scipy.signal.lfilter
     
        TODO: the window parameter could be the window itself if an array instead of a string
        NOTE: length(output) != length(input), to correct this: return y[(window_len/2-1):-(window_len/2)] instead of just y.
        """
    
        if x.ndim != 1:
            raise ValueError, "smooth only accepts 1 dimension arrays."
    
        if x.size < window_len:
            raise ValueError, "Input vector needs to be bigger than window size."
    
    
        if window_len<3:
            return x
    
    
        if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
            raise ValueError, "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"
    
    
        s=np.r_[x[window_len-1:0:-1],x,x[-1:-window_len:-1]]
        if window == 'flat': #moving average
            w=np.ones(window_len,'d')
        else:
            w=eval('np.'+window+'(window_len)')
    
        y=np.convolve(w/w.sum(),s,mode='valid')
        return y
    
    def label(self, onlyOne=True):

        labeled, nr_objects = ndimage.label(self.__img)
        print 'Number of components: ' + str(nr_objects)
        #if nr_objects>2: return None
        if nr_objects==0: return None
        val=labeled.flatten()
        hist = []
        hist+=range(np.max(val) + 1)
        test, _ = np.histogram(val, hist)
        comp1 = np.max(test)
        idx1 = list(test).index(comp1)

        
        if nr_objects>1:  
            test[idx1] = 0      
            comp2 = np.max(test)
            idx2 = list(test).index(comp2)
            test[idx2] = 0
        else:
            idx2=1
    
        idx = np.where(labeled==idx2)
        #bounding box
        iMin=np.min(idx[0])
        jMin=np.min(idx[1])
        iMax=np.max(idx[0])
        jMax=np.max(idx[1])

        return labeled[iMin:iMax, jMin:jMax] #just return the cropped image of the largest component
    

    def labelAll(self):
        labeled, nr_objects = ndimage.label(self.__img)
        return labeled, nr_objects

    def findCircle(self,hist, labled):
        compsX = []
        compsY = []
        for i in range(len(hist) + 1):
            compsX.append([])
            compsY.append([])
        h, w = np.shape(labled)
        for i in range(w):
            for j in range(h):
                compsX[labled[j][i]].append(j)
                compsY[labled[j][i]].append(i)
        ratio = []        
        for i in range(len(compsX)):
            xMin = np.min(compsX[i])
            xMax = np.max(compsX[i])
            yMin = np.min(compsY[i])
            yMax = np.max(compsY[i])
            if yMax - yMin > w/200:
                if yMax - yMin < w/10:
                    if ratio < 0.2:
                        ratio.append((float(xMax) - float(xMin)) / (float(yMax) - float(yMin)))
                else:
                    ratio.append(-1)
            else:
                    ratio.append(-1)
        
        circleRatio = 1
        circleIdx = 0             
        for i in range(len(ratio)):
            if ratio[i] >= 0:
                if np.abs(1 - ratio[i]) < circleRatio:
                    circleRatio = np.abs(1 - ratio[i])
                    circleIdx = i
        xMin = np.min(compsX[circleIdx])
        xMax = np.max(compsX[circleIdx])
        yMin = np.min(compsY[circleIdx])
        yMax = np.max(compsY[circleIdx])         
                       
        return circleIdx, circleRatio, float(xMax) - float(xMin), float(yMax) - float(yMin)
    
    def findThickestPath(self,skelImg,skelDia,xScale,yScale):
        print 'create skeleton graph'
        skelGraph,skelSize=self.makeGraphFast(skelImg,skelDia,xScale,yScale)
        rootVertex,_=self.findRootVertex(skelGraph)
        epropW=skelGraph.edge_properties["w"]
        
        maxDia=np.max(skelDia)
        maxDia10=np.max(skelDia[0:len(skelDia)*0.1])
        print 'max Diameter: '+ str(maxDia)
        path=[]
        #remove all two-connected ones with 0 label
        print 'trace path of thickest diameter'
        #find thickest path
        pathDetect=True
        if skelGraph.num_vertices() >0:
            
            pathDetect=True
            while pathDetect==True:
                lastVertex=self.findLastRootVertex(skelGraph)
                try:
                    path,_=gt.shortest_path(skelGraph, rootVertex, lastVertex , weights=epropW, pred_map=None)
                    pathDetect=False
                except:
                    raise
                    if lastVertex <=0: 
                        pathDetect=False
                    else:
                        skelGraph.remove_vertex(lastVertex)
                        lastVertex=self.findLastRootVertex(skelGraph)

        return path,skelGraph,maxDia10,skelSize   
                
    def findThickestPathLateral(self,skelImg,skelDia,xScale,yScale):
        print 'create skeleton graph'
        skelGraph,_=self.makeGraphFast(skelImg,skelDia,xScale,yScale)
        rootVertex=self.findRootVertexLateral(skelGraph)
        epropW=skelGraph.edge_properties["w"]

        path=[]
        #remove all two-connected ones with 0 label
        print 'trace path of thickest diameter'
        #find thickest path
        pathDetect=True
        if skelGraph.num_vertices() >0:
            pathDetect=True
            while pathDetect==True:
                lastVertex=self.findLastRootVertex(skelGraph)
                try:
                    path,_=gt.shortest_path(skelGraph, rootVertex, lastVertex , weights=epropW, pred_map=None)
                    pathDetect=False
                except:
                    raise
                    if lastVertex <=0: 
                        pathDetect=False
                    else:
                        skelGraph.remove_vertex(lastVertex)
                        lastVertex=self.findLastRootVertex(skelGraph)
                        
        return path,skelGraph 
    
    def makeGraphFast(self,img,dia,xScale,yScale):
        print('Building Graph Data Structure'),
        start=time.time()
        G = Graph(directed=False)
        sumAddVertices=0
        
        vprop=G.new_vertex_property('object')
        eprop=G.new_edge_property('object')
        epropW=G.new_edge_property("float")
        h, w = np.shape(img)
        if xScale>0 and yScale>0: avgScale=(xScale+yScale)/2
        else: 
            avgScale=1.
            xScale=1.
            yScale=1.
        addedVerticesLine2=[]
        vListLine2=[]
        percentOld=0
        counter=0
        '''
        Sweep over each line in the image except the last line
        '''
        for idx,i in enumerate(img[:len(img)-2]):
            '''
            Get foreground indices in the current line of the image and make vertices
            '''
            counter+=1
            percent=(float(counter)/float(h))*100
            if percentOld+10< percent: 
                print (str(np.round(percent,1))+'% '),
                percentOld=percent

            line1=np.where(i==True)
            if len(line1[0])>0:
                line1=set(line1[0]).difference(set(addedVerticesLine2))
                vL=G.add_vertex(len(list(line1)))
                
                
                if len(line1)>1 : 
                    vList=vListLine2+list(vL)
                else: vList=vListLine2+[vL]
                line1=addedVerticesLine2+list(line1)
                for jdx,j in enumerate(line1):
                    vprop[vList[jdx]]={'imgIdx':(j,idx),'coord': (float(j)*xScale,float(idx)*yScale), 'nrOfPaths':0, 'diameter':float(dia[idx][j])*avgScale}
                '''
                keep order of the inserted vertices
                '''
                sumAddVertices+=len(line1)
                
                addedVerticesLine2=[]
                vListLine2=[]
                '''
                Connect foreground indices to neighbours in the next line
                '''
                for v1 in line1:
                    va=vList[line1.index(v1)]
                    diagonalLeft = diagonalRight = True
                    try:
                        if img[idx][v1-1]==True:
                            diagonalLeft=False
                            vb=vList[line1.index(v1-1)]
                            e=G.add_edge(va,vb)
                            eprop[e]={'coord1':vprop[va]['coord'], 'coord2':vprop[vb]['coord'],'weight':((vprop[va]['diameter']+vprop[vb]['diameter'])/2),'RTP':False}
                            epropW[e]=2./(eprop[e]['weight']**2)
                    except:
                        print 'Boundary vertex at: '+str([v1,idx-1])+' image size: '+ str([w,h])
                        pass
                    
                    try:
                        if img[idx][v1+1]==True:
                            diagonalRight=False
                            vb=vList[line1.index(v1+1)]
                            e=G.add_edge(va,vb)
                            eprop[e]={'coord1':vprop[va]['coord'], 'coord2':vprop[vb]['coord'],'weight':((vprop[va]['diameter']+vprop[vb]['diameter'])/2),'RTP':False}
                            epropW[e]=2./(eprop[e]['weight']**2)
                    except:
                        print 'Boundary vertex at: '+str([v1+1,idx])+' image size: '+ str([w,h])
                        pass # just if we are out of bounds
                    
                    try:
                        if img[idx+1][v1]==True:
                            diagonalRight=False
                            diagonalLeft=False
                            vNew=G.add_vertex()
                            vprop[vNew]={'imgIdx':(v1,idx+1),'coord': (float(v1)*xScale,float(idx+1)*yScale), 'nrOfPaths':0, 'diameter':float(dia[idx+1][v1])*avgScale}
                            vListLine2.append(vNew)
                            e=G.add_edge(vList[line1.index(v1)],vNew)
                            eprop[e]={'coord1':vprop[va]['coord'], 'coord2':vprop[vNew]['coord'],'weight':((vprop[va]['diameter']+vprop[vNew]['diameter'])/2),'RTP':False}
                            epropW[e]=1./(eprop[e]['weight']**2)
                            if v1 not in addedVerticesLine2: addedVerticesLine2.append(v1)
                    except:
                        print 'Boundary vertex at: '+str([v1,idx+1])+' image size: '+ str([w,h])
                        pass
                    
                    try:    
                        if diagonalRight == True and img[idx+1][v1+1]==True:
                            vNew=G.add_vertex()
                            vprop[vNew]={'imgIdx':(v1+1,idx+1),'coord': (float(v1+1)*xScale,float(idx+1)*yScale), 'nrOfPaths':0, 'diameter':float(dia[idx+1][v1+1])*avgScale}
                            vListLine2.append(vNew)
                            e=G.add_edge(vList[line1.index(v1)],vNew)
                            eprop[e]={'coord1':vprop[va]['coord'], 'coord2':vprop[vNew]['coord'],'weight':((vprop[va]['diameter']+vprop[vNew]['diameter'])/2),'RTP':False}
                            epropW[e]=1.41/(eprop[e]['weight']**2)
                            if v1+1 not in addedVerticesLine2: addedVerticesLine2.append(v1+1)
                    except:
                        print 'Boundary vertex at: '+str([v1+1,idx+1])+' image size: '+ str([w,h])
                        pass
                    
                    try:
                        if diagonalLeft  == True and img[idx+1][v1-1]==True:
                            vNew=G.add_vertex()
                            vprop[vNew]={'imgIdx':(v1-1,idx+1),'coord': (float(v1-1)*xScale,float(idx+1)*yScale), 'nrOfPaths':0, 'diameter':float(dia[idx+1][v1-1])*avgScale}
                            vListLine2.append(vNew)
                            e=G.add_edge(vList[line1.index(v1)],vNew)
                            eprop[e]={'coord1':vprop[va]['coord'], 'coord2':vprop[vNew]['coord'],'weight':((vprop[va]['diameter']+vprop[vNew]['diameter'])/2),'RTP':False}
                            epropW[e]=1.41/(eprop[e]['weight']**2)
                            if v1-1 not in addedVerticesLine2: addedVerticesLine2.append(v1-1)
                    except:
                        print 'Boundary vertex at: '+str([v1-1,idx+1])+' image size: '+ str([w,h])
                        pass
                    try:
                        if img[idx][v1+1]==False and img[idx][v1-1]==False and img[idx+1][v1]==False and diagonalLeft==False and diagonalRight==False:
                            print 'tip detected'
                            if img[idx-1][v1-1]==False and img[idx-1][v1+1]==False and img[idx-1][v1]==False:
                                print 'floating pixel'
                    except:
                        pass
        
        print'done!'                               
        G.edge_properties["ep"] = eprop
        G.edge_properties["w"] = epropW
        G.vertex_properties["vp"] = vprop            
        print 'graph build in '+str(time.time()-start)
        l = gt.label_largest_component(G)
        u = gt.GraphView(G, vfilt=l)
        print '# vertices'
        print(u.num_vertices())
        print(G.num_vertices())
        if u.num_vertices()!=G.num_vertices(): self.__fail=float((G.num_vertices()-u.num_vertices()))/float(G.num_vertices())
        return u,u.num_vertices()
 
    def makeGraph(self,img,dia,xScale,yScale):
        print 'Building Graph Data Structure'
        start=time.time()
        G = Graph(directed=False)
        vprop=G.new_vertex_property('object')
        eprop=G.new_edge_property('object')
        epropW=G.new_edge_property("int32_t")
        avgScale=(xScale+yScale)/2

        test=np.where(img==True)
        ss = np.shape(test)
        cccc=0
        percentOld=0.0
        print str(np.round(percentOld,1))+'%'
        for (i,j) in zip(test[1],test[0]):
                cccc+=1
                percent=(float(cccc)/float(ss[1]))*100
                if percentOld+10< percent: 
                    print str(np.round(percent,1))+'%'
                    percentOld=percent
                nodeNumber1 = (float(i)*yScale,float(j)*xScale)
                if gu.find_vertex(G, vprop, {'imgIdx':(j,i),'coord':nodeNumber1, 'nrOfPaths':0, 'diameter':float(dia[j][i])*avgScale}):
                            v1=gu.find_vertex(G, vprop, {'imgIdx':(j,i),'coord':nodeNumber1, 'nrOfPaths':0, 'diameter':float(dia[j][i])*avgScale})[0]
                else:
                    v1=G.add_vertex()
                    vprop[G.vertex(v1)]={'imgIdx':(j,i),'coord':nodeNumber1, 'nrOfPaths':0, 'diameter':float(dia[j][i])*avgScale}
                try:
                    
                    if img[j,i+1] == True:
                        nodeNumber2 = (float(i+1)*yScale,float(j)*xScale)
                        if gu.find_vertex(G, vprop, {'imgIdx':(j,i+1),'coord':nodeNumber2, 'nrOfPaths':0, 'diameter':float(dia[j][i+1])*avgScale}):
                            v2=gu.find_vertex(G, vprop, {'imgIdx':(j,i+1),'coord':nodeNumber2, 'nrOfPaths':0, 'diameter':float(dia[j][i+1])*avgScale})[0]
                            if gu.find_edge(G, eprop, {'coord1':vprop[v2]['coord'], 'coord2':vprop[v1]['coord'],'weight':((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)**4,'RTP':False}):
                                pass
                            else:
                                e = G.add_edge(v1, v2)
                                epropW[e]=(((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)/avgScale)**4
                                eprop[e]={'coord1':vprop[v1]['coord'], 'coord2':vprop[v2]['coord'],'weight':((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)**4,'RTP':False}
                        else:
                            v2=G.add_vertex()
                            vprop[G.vertex(v2)]={'imgIdx':(j,i+1),'coord':nodeNumber2, 'nrOfPaths':0, 'diameter':float(dia[j][i+1])*avgScale}
                            e = G.add_edge(v1, v2)
                            epropW[e]=(((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)/avgScale)**4
                            eprop[e]={'coord1':vprop[v1]['coord'], 'coord2':vprop[v2]['coord'],'weight':((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)**4,'RTP':False}
                except:
                    pass
                try:
                    if img[j,i-1] == True:
                        nodeNumber2 = (float(i-1)*yScale,float(j)*xScale)
                        if gu.find_vertex(G, vprop, {'imgIdx':(j,i-1),'coord':nodeNumber2, 'nrOfPaths':0, 'diameter':float(dia[j][i-1])*avgScale}):
                            v2=gu.find_vertex(G, vprop, {'imgIdx':(j,i-1),'coord':nodeNumber2, 'nrOfPaths':0, 'diameter':float(dia[j][i-1])*avgScale})[0]
                            if gu.find_edge(G, eprop, {'coord1':vprop[v2]['coord'], 'coord2':vprop[v1]['coord'],'weight':((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)**4,'RTP':False}):
                                pass
                            else:
                                e = G.add_edge(v1, v2)
                                epropW[e]=(((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)/avgScale)**4
                                eprop[e]={'coord1':vprop[v1]['coord'], 'coord2':vprop[v2]['coord'],'weight':((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)**4,'RTP':False}
                        else:
                            v2=G.add_vertex()
                            vprop[G.vertex(v2)]={'imgIdx':(j,i-1),'coord':nodeNumber2, 'nrOfPaths':0, 'diameter':float(dia[j][i-1])*avgScale}
                            e = G.add_edge(v1, v2)
                            epropW[e]=(((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)/avgScale)**4
                            eprop[e]={'coord1':vprop[v1]['coord'], 'coord2':vprop[v2]['coord'],'weight':((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)**4,'RTP':False}
                except:pass
                try:
                    if img[j + 1,i] == True:
                        nodeNumber2 = (float(i)*yScale,float(j+1)*xScale)
                        if gu.find_vertex(G, vprop, {'imgIdx':(j+1,i),'coord':nodeNumber2, 'nrOfPaths':0, 'diameter':float(dia[j+1][i])*avgScale}):
                            v2=gu.find_vertex(G, vprop, {'imgIdx':(j+1,i),'coord':nodeNumber2, 'nrOfPaths':0, 'diameter':float(dia[j+1][i])*avgScale})[0]
                            if gu.find_edge(G, eprop, {'coord1':vprop[v2]['coord'], 'coord2':vprop[v1]['coord'],'weight':((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)**4,'RTP':False}):
                                pass
                            else:
                                e = G.add_edge(v1, v2)
                                epropW[e]=(((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)/avgScale)**4
                                eprop[e]={'coord1':vprop[v1]['coord'], 'coord2':vprop[v2]['coord'],'weight':((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)**4,'RTP':False}
                        else:
                            v2=G.add_vertex()
                            vprop[G.vertex(v2)]={'imgIdx':(j+1,i),'coord':nodeNumber2, 'nrOfPaths':0, 'diameter':float(dia[j+1][i])*avgScale}
                            e = G.add_edge(v1, v2)
                            epropW[e]=(((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)/avgScale)**4
                            eprop[e]={'coord1':vprop[v1]['coord'], 'coord2':vprop[v2]['coord'],'weight':((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)**4,'RTP':False}
                except:pass
                try:
                    if img[j - 1,i] == True:
                        nodeNumber2 = (float(i)*yScale,float(j-1)*xScale)
                        if gu.find_vertex(G, vprop, {'imgIdx':(j-1,i),'coord':nodeNumber2, 'nrOfPaths':0, 'diameter':float(dia[j-1][i])*avgScale}):
                            v2=gu.find_vertex(G, vprop, {'imgIdx':(j-1,i),'coord':nodeNumber2, 'nrOfPaths':0, 'diameter':float(dia[j-1][i])*avgScale})[0]
                            if gu.find_edge(G, eprop, {'coord1':vprop[v2]['coord'], 'coord2':vprop[v1]['coord'],'weight':((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)**4,'RTP':False}):
                                pass
                            else:
                                e = G.add_edge(v1, v2)
                                epropW[e]=(((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)/avgScale)**4
                                eprop[e]={'coord1':vprop[v1]['coord'], 'coord2':vprop[v2]['coord'],'weight':((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)**4,'RTP':False}
                        else:
                            v2=G.add_vertex()
                            vprop[G.vertex(v2)]={'imgIdx':(j-1,i),'coord':nodeNumber2, 'nrOfPaths':0, 'diameter':float(dia[j-1][i])*avgScale}
                            e = G.add_edge(v1, v2)
                            epropW[e]=(((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)/avgScale)**4
                            eprop[e]={'coord1':vprop[v1]['coord'], 'coord2':vprop[v2]['coord'],'weight':((vprop[v1]['diameter']+vprop[v2]['diameter'])/2)**4,'RTP':False}
                except: pass
#                    
        print '100.0%'
        print 'selecting largest connected component'
        G.edge_properties["ep"] = eprop
        G.edge_properties["w"] = epropW
        G.vertex_properties["vp"] = vprop
        l = gt.label_largest_component(G)
        print(l.a)
        u = gt.GraphView(G, vfilt=l)
        print '# vertices'
        print(u.num_vertices())
        print(G.num_vertices())
        print '# edges'
        print(u.num_edges())
        print 'building graph finished in: '+str(time.time()-start)+'s'
        return u 
    
    def findRootVertex(self,G):
        print 'finding root vertex X'
        h=self.__height
        vertexIndex = 0
        dTmp=0
        dMax=0
        vprop=G.vertex_properties["vp"]
        for v in G.vertices():
            count=0
            for _ in v.out_neighbours():
                count+=1
                if count >2:
                    break 
            if count>2:
                dTmp=vprop[v]['diameter']
                if vprop[v]['imgIdx'][1] < h:
                    dMax=dTmp
                    h = vprop[v]['imgIdx'][1]
                    vertexIndex = v
        return vertexIndex,dMax
    
    def findRootVertexLateral(self,G):
        print 'finding root vertex X'
        h=self.__height
        vertexIndex = 0

        vprop=G.vertex_properties["vp"]
        
        for v in G.vertices():
            if vprop[v]['imgIdx'][1] < h:
                    h = vprop[v]['imgIdx'][1]
                    vertexIndex = v
        return vertexIndex
    
    def findLastRootVertex(self,G):
        dpath =0
        vertexIndex = 0
        vprop=G.vertex_properties["vp"]
        for i in G.vertices():
            try:
                if vprop[i]['imgIdx'][1] > dpath:
                    dpath = vprop[i]['imgIdx'][1]
                    vertexIndex = i
            except:
                pass
        return vertexIndex
    
    def findLaterals(self,RTP,G,scale,path):
        if scale ==0.:
            scale=1.
        corresBranchPoints=[]
        laterals=[]
        distToFirstLateral=2000000000000000.
        vprop=G.vertex_properties["vp"]
        idx=self.findRootVertexLateral(G)
        for i in RTP:
            if len(i)>0:
                for bp in i:
                    d=float(vprop[G.vertex(bp)]['diameter'])
                    radius=int(d/scale) # convert radius at branching point to pixels
                    #print d,radius
                    if radius>0:
                        break

            # remove the radius from of the main trunk from the lateral length 
            # to obtain the emerging lateral length from the surface
             
            if radius+2< len(i):
                lBranch=len(i[:radius])
                laterals.append(i[radius:])
                corresBranchPoints.append(i[0])

        #if path is not given, then no distance to first lateral is computed
        if path!=None:
            
            x=vprop[G.vertex(idx)]['imgIdx'][0] # Note idx is a vertex object
            y=vprop[G.vertex(idx)]['imgIdx'][1]
            
            for i in corresBranchPoints:
                try:
                    ix=vprop[G.vertex(i)]['imgIdx'][0] #Note: i is an index and the vertex object has to be called
                    iy=vprop[G.vertex(i)]['imgIdx'][1]
                    d=(ix-x)**2+(iy-y)**2
                    if d < distToFirstLateral:
                        distToFirstLateral=np.sqrt(d)
                except:
                    pass
        
        if path == None:
            return laterals,corresBranchPoints
        else:
            return laterals,corresBranchPoints,distToFirstLateral*scale
    
    
    def findHypocotylCluster(self,thickestPath,rtpSkel):
        print 'find Cluster'
        branchingPaths=[]
        branchingPoints=[]
        radius=[]
        vprop= rtpSkel.vertex_properties["vp"]
        for i in thickestPath:
            # if len(nx.neighbors(rtpSkel, i))>2:
                branchingPaths.append(vprop[i]['nrOfPaths'])
                branchingPoints.append(i)
                #radius.append(rtpSkel.node[i]['diameter'])

        for i in branchingPoints:         
            radius.append(vprop[i]['diameter'])
            
        bp=[]
        rad=[]    
        tmpAvg=0.
        counter=0.
        for i in range(len(branchingPoints)-1):
            if branchingPaths[i]==branchingPaths[i+1]:
                tmpAvg+=radius[i]
                counter+=1
            elif counter>0:
                tmpAvg=tmpAvg/counter 
                rad.append(tmpAvg)
                bp.append(branchingPaths[i])
                counter=0.
                tmpAvg=0.
        
        return bp,rad
                
    def makeSegmentationPicture(self,thickestPath,G,crownImg,xScale,yScale,c1x,c1y,c2x,c2y,c3x=None,c3y=None):

        print 'make cluster picture'
        crownImg=m.as_rgb(crownImg,crownImg,crownImg)
        vprop=G.vertex_properties["vp"]
        for i in thickestPath:

            if vprop[i]['nrOfPaths'] in c1y:

                y=int(vprop[i]['imgIdx'][0])
                x=int(vprop[i]['imgIdx'][1])
                try: crownImg[x][y]=(125,0,0)
                except: pass
                dia=vprop[i]['diameter']/(xScale/2+yScale/2)
                dia=dia*1.5
                for j in range(int(dia)):
                    try: crownImg[x][y+j]=(125,0,0)
                    except: pass
                    try: crownImg[x][y-j]=(125,0,0)
                    except: pass
                    try: crownImg[x-j][y]=(125,0,0)
                    except: pass
                    try: crownImg[x+j][y]=(125,0,0)
                    except: pass
            elif vprop[i]['nrOfPaths'] in c2y:
                y=int(vprop[i]['imgIdx'][0])
                x=int(vprop[i]['imgIdx'][1])
                try: crownImg[x][y]=(125,0,0)
                except: pass
                dia=vprop[i]['diameter']/(xScale/2+yScale/2)
                dia=dia*1.5
                for j in range(int(dia)):
                    try: crownImg[x][y+j]=(0,125,0)
                    except: pass
                    try: crownImg[x][y-j]=(0,125,0)
                    except: pass
                    try: crownImg[x-j][y]=(0,125,0)
                    except: pass
                    try: crownImg[x+j][y]=(0,125,0)
                    except: pass
                y=int(vprop[i]['imgIdx'][0])
                x=int(vprop[i]['imgIdx'][1])
                try: crownImg[x][y]=(0,0,125)
                except: pass
                dia=vprop[i]['diameter']/(xScale/2+yScale/2)
                dia=dia*1.5
                for j in range(int(dia)):
                    try: crownImg[x][y+j]=(0,0,125)
                    except: pass
                    try: crownImg[x][y-j]=(0,0,125)
                    except: pass
                    try: crownImg[x-j][y]=(0,0,125)
                    except: pass
                    try: crownImg[x+j][y]=(0,0,125)
                    except: pass
        return crownImg
        
            

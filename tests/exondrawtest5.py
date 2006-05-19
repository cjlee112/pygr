#!/usr/bin/env python
# modified from visualpygr.py to use SVGdraw instead of OpenGL


from SVGdraw import *
#from pygr import *
# test exondraw()
#this version adds pop-up labels. also on mouse click-it colors the exon temporarily

ecmascript="""

var svgObjLabel;
var svgDoc;
var obj = evt.getTarget();

function init(evt){
		var directTarget=evt.getTarget();
		svgObjLabel=svgDocument.getElementById("label");
		svgObjLabel=svgObjLabel.getFirstChild();
		}
		
function showLabel(name){
		svgObjLabel.setData(name);
	   	}
	
function emptyLabel(){
		svgObjLabel.setData("");
	}
	
function showColor(evt){
		obj.setAttribute('fill', 'gray');
	}
	
	"""
	

def spliceColor(e, e1, spl):
	if spl.type=='U11/U12':
		color='green'    #U11/U12 splices colored green
		
	elif spl.type=='U1/U2' and len(e.next)>1:
		color='red'         #alt U1/U2 spls colored red
	else:
		color='yellow'     #all others colored yellow
		
	return color
				
	
	
def spliceDraw(e, e1, spl, ysplStart, ysplHeight, transform):
	xs0=transform(spl.ver_gen_start)            #call object as function to get xout from xin
	xs1=transform(spl.ver_gen_end)               #same as above
	label="showLabel('Splice %d starts at %d and ends at %d')" % (spl.id, spl.ver_gen_start, spl.ver_gen_end)
	splicecolor=spliceColor(e, e1, spl)
	if spl.id%2==0:     #if s.id is even-spl drawn upwards
		pd=pathdata(x=xs0, y=40)
		pd.line(x=(xs0+xs1)/2, y=20)
		pd.line(x=xs1, y=40)
	else:     #if sid is odd spl drwan downwards
		pd=pathdata(x=xs0, y=60)
		pd.line(x=(xs0+xs1)/2, y=80)
		pd.line(x=xs1, y=60)
		
	return path(pd, stroke=splicecolor, stroke_width=0.5, fill='none', onmouseover=label, onmouseout="emptyLabel()")  #check if this stroke_width is ok
	
	
def exonColor(e, left_splice, right_splice):
	if e in left_splice and e in right_splice:          #is this an internal exon?
		if (left_splice[e]=='U1/U2' and right_splice[e]=='U1/U2'):
			color='yellow'     #majority internal ag-gt exons colored yellow?
		else:
			color='red'   #all other (atypical) exons are red. Later write color for terminal exons
		
	else:
		color='blue'     #terminal exons blue?
	
	return color

def exonDraw(e, y, exonheight, transform):                   #do I need to keep exonheight a variable?
	xs0=transform(e.genomic_start)            #call object as function to get xout from xin
	xs1=transform(e.genomic_end)               #same as above
	label="showLabel('Exon %d starts at %d and ends at %d')" % (e.id, e.genomic_start, e.genomic_end)
	return rect(x=xs0, y=y, width=xs1-xs0, height=exonheight,  fill='none', stroke_width=0.5, stroke='black', onmouseover=label, onmouseout="emptyLabel()", onclick="showColor(evt)")  



class XTransform(object):             #create class to scale gene picture-returns x out from xin
	def __init__(self,xIn0,xIn1,xOut0,xOut1,padding=0):
		xOut0=xOut0+padding        # apply padding on both sides
		xOut1=xOut1-padding
		widthIn=xIn1-xIn0    #same as gen_length?
		widthOut=xOut1-xOut0   #svg window scale
		self.scaleFactor=widthIn/float(widthOut)    #need float format.  Float conversion applied here
		self.slideFactor=(xIn0/self.scaleFactor)-xOut0    #this equation doesnt assume that xOut0 is zero

	def __call__(self,xIn):                   #to use the object as a function
		xOut=(xIn-(self.scaleFactor*self.slideFactor))/self.scaleFactor
		return xOut
		

def draw(exons, gen_length, file_name, gen_start):                                 #this func sets viewbox, calls scale fn and draws gene, default gene_start=0
	d=drawing()   #open drawing
	s=svg((0,0,300,150),'30cm','15cm',  onload="init(evt)")   #create svg root element. Viewbox will be reset later in draw fns scaling calc. onload evt initializes variables for the ecmascript
	ds=description('SVGpygrtest')    #set description
	s.addElement(ds)  
	scr=script(type="text/ecmascript", cdata=ecmascript)   #add script to root svg
	s.addElement(scr)
	t=text(x=100, y=120, font_size=8, stroke='black', stroke_width=0.5, text="none", id="label")   #add position on viewbox with id 'label'
	s.addElement(t)
	t=XTransform(gen_start,gen_start+gen_length,0,300, 10)       #creates the transform object, used as a func later.  Padding is optional
	exonheight=20
	left_splice={}                 #creates a dictionary contg info about left spl
	right_splice={}               #creates a dict contg info about rt spl
	for e in exons:                   #this stores info in 2 dictionaries with infor about whether there are spls on either end and splice info
		for e1,spl in e.next.items():
			left_splice[e1]=spl.type
			right_splice[e]=spl.type
		
		
			
	for e in exons:                                  #the design decision is to draw each exon seperately
		color=exonColor(e, left_splice, right_splice)	
		r=exonDraw(e, 40, 20, t)    #exondraw fn returns a rect, r
		r.attributes['stroke']=color
		s.addElement(r)                     #add r to svg
		
	
	for e in exons:
		for e1,spl in e.next.items():
			p=spliceDraw(e, e1, spl, 40, 20, t)
			s.addElement(p)
	
	d.setSVG(s)  #set drawing to root svg element
	
	d.toXml(file_name)  #Xmlify the code and again, put in cluster_id from database
		
		
		
#DummyExon, DummySplice and exoninit are added to test the code            
            
class DummyExon(object):
	def __init__(self,start,end):
		self.gen_start=start
		self.gen_end=end
		self.next={}   #creates dict

class DummySplice(object):
	def __init__(self,start,end):
		self.ver_gen_start=start
		self.ver_gen_end=end


def exonInit():
	l=[]
	l.append(DummyExon(1000,1150))
	l.append(DummyExon(1500,1650))
	l.append(DummyExon(2000,2150))
	l[0].next[l[1]]=DummySplice(1150, 1500)    # puts in dict where key is next exon and value is splice
	l[0].next[l[2]]=DummySplice(1150, 2000)    # key is next exon and value is splice
	l[1].next[l[2]]=DummySplice(1650, 2000)    # key is next exon and value is splice
	return l



def main():
	#exons=exonInit()  #for testing.  This gives dummy exon and dummy splice info
	#gen_length=1150.00 #this is only for testing- float variable
	#gen_length=gen_length*1.5  #so that gene doesnt take up whole screen 
	#gen_start=1000.00  #for testing - float variable
	draw(exons, gen_length, 'exondrawtest.svg', gen_start)  #The file_name here is only for testing.  this func sets viewBox, svg root, draws the gene, and Xmlifies it
	
	

	
if __name__=='__main__': main()
	

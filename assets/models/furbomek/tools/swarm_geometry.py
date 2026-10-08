"""Deterministic, mesh-native miniature construction tools. Front is -Y."""
import bpy, math, random
from mathutils import Vector, Matrix
from math import sin, cos, pi

class Builder:
    def __init__(self,name):
        self.name=name
        self.collection=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(self.collection)
        self.root=bpy.data.objects.new(name+'_ROOT',None); self.collection.objects.link(self.root)
        self.steel=self.mat('dark steel',(.13,.15,.15),.75)
        self.armor=self.mat('warm painted alloy',(.43,.44,.40),.52)
        self.edge=self.mat('machined edges',(.63,.65,.61),.8,.3)
        self.black=self.mat('recesses',(.015,.019,.022),.15)
    def mat(self,name,color,metal=0,rough=.45):
        m=bpy.data.materials.new(self.name+' '+name); m.diffuse_color=(*color[:3],1); m.use_nodes=True
        p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=m.diffuse_color; p.inputs['Metallic'].default_value=metal; p.inputs['Roughness'].default_value=rough
        return m
    def mesh(self,name,vertices,faces,mat,bevel=0):
        m=bpy.data.meshes.new(name); m.from_pydata(vertices,[],faces); m.update()
        o=bpy.data.objects.new(name,m); self.collection.objects.link(o); o.parent=self.root
        if mat:m.materials.append(mat)
        if bevel:
            mod=o.modifiers.new('manufactured edge radii','BEVEL'); mod.width=bevel; mod.segments=2
            mod=o.modifiers.new('weighted corner normals','WEIGHTED_NORMAL')
        return o
    def box(self,name,loc,half,mat,bevel=.02,rotation=None):
        h=half; v=[(x*h[0],y*h[1],z*h[2]) for z in [-1,1] for y in [-1,1] for x in [-1,1]]
        o=self.mesh(name,v,[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)],mat,bevel); o.location=loc
        if rotation:o.rotation_euler=rotation
        return o
    def sphere(self,name,loc,scale,mat):
        v=[]; f=[]; n=32; k=20
        for j in range(k+1):
            t=pi*j/k
            for i in range(n):
                p=2*pi*i/n; v.append((sin(t)*cos(p)*scale[0],sin(t)*sin(p)*scale[1],cos(t)*scale[2]))
        for j in range(k):
            for i in range(n):a=j*n+i;b=j*n+(i+1)%n;f.append((a,b,b+n,a+n))
        o=self.mesh(name,v,f,mat);o.location=loc
        for p in o.data.polygons:p.use_smooth=True
        return o
    def cone(self,name,a,b,r0,r1,mat,verts=24):
        a,b=Vector(a),Vector(b);d=b-a;q=d.to_track_quat('Z','Y');v=[]
        for z,r in [(0,r0),(d.length,r1)]:
            for i in range(verts):v.append(tuple(a+q@Vector((r*cos(2*pi*i/verts),r*sin(2*pi*i/verts),z))))
        f=[tuple(reversed(range(verts))),tuple(range(verts,2*verts))]+[(i,(i+1)%verts,(i+1)%verts+verts,i+verts) for i in range(verts)]
        o=self.mesh(name,v,f,mat)
        for p in list(o.data.polygons)[2:]:p.use_smooth=True
        return o
    def cyl(self,name,a,b,r,mat,verts=32):return self.cone(name,a,b,r,r,mat,verts)
    def torus(self,name,loc,r,minor,mat,axis=(0,1,0)):
        q=Vector(axis).to_track_quat('Z','Y');c=Vector(loc);v=[];f=[];n=40;m=8
        for i in range(n):
            t=2*pi*i/n
            for j in range(m):
                p=2*pi*j/m;v.append(tuple(c+q@Vector(((r+minor*cos(p))*cos(t),(r+minor*cos(p))*sin(t),minor*sin(p)))))
        for i in range(n):
            for j in range(m):f.append((i*m+j,((i+1)%n)*m+j,((i+1)%n)*m+(j+1)%m,i*m+(j+1)%m))
        o=self.mesh(name,v,f,mat)
        for p in o.data.polygons:p.use_smooth=True
        return o
    def tube(self,name,points,r,mat):
        v=[];f=[];n=8
        for i,p in enumerate(points):
            p=Vector(p);d=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)]);q=d.to_track_quat('Z','Y')
            for j in range(n):v.append(tuple(p+q@Vector((r*cos(j*2*pi/n),r*sin(j*2*pi/n),0))))
        for i in range(len(points)-1):
            for j in range(n):f.append((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j))
        return self.mesh(name,v,f,mat)
    def bolt(self,loc,axis,scale=.035):
        c=Vector(loc);a=Vector(axis).normalized();return self.cone('hex fastener',c-a*.007,c+a*.018,scale,scale,self.edge,6)
    def panel(self,name,vertices,mat,depth=.025):
        vs=[Vector(v) for v in vertices];n=(vs[1]-vs[0]).cross(vs[2]-vs[0]).normalized();l=len(vs)
        return self.mesh(name,[tuple(v) for v in vs]+[tuple(v-n*depth) for v in vs],[tuple(range(l)),tuple(reversed(range(l,2*l)))]+[(i,(i+1)%l,(i+1)%l+l,i+l) for i in range(l)],mat,.012)
    def head(self,center,scale=1,color=(.85,.85,.8),ear_inner=(.3,.3,.3),style='fur',ears=True,beak=(.9,.58,.025)):
        c=Vector(center);s=scale; old=set(self.collection.objects)
        fur=self.mat('soft fur',color,0,.92); cream=self.mat('ivory eye mask',(.9,.89,.78),0,.43);dark=self.black
        iris=self.mat('smoky iris',(.23,.32,.27),.05,.23);yellow=self.mat('split beak',beak,0,.3);inside=self.mat('ear velvet',ear_inner,0,.86)
        def P(x,y,z):return c+Vector((x,y,z))*s
        # Broad lower pear and gently narrower crown, continuous parametric shell.
        v=[];f=[];N=48;K=32
        def surface(t,p):
            z=cos(t)*.68;w=.51*(1-.22*cos(t));return Vector((sin(t)*cos(p)*w,sin(t)*sin(p)*.39,z))
        for j in range(K+1):
            for i in range(N):v.append(tuple(c+surface(pi*j/K,2*pi*i/N)*s))
        for j in range(K):
            for i in range(N):a=j*N+i;b=j*N+(i+1)%N;f.append((a,b,b+N,a+N))
        o=self.mesh('pear fur skin',v,f,fur)
        for p in o.data.polygons:p.use_smooth=True
        if style=='blackwhite':
            o.data.materials.append(dark)
            for poly in o.data.polygons:
                p=poly.center
                p=(p-c)/s
                if (abs(p.x)>.35 and p.z<.30) or (abs(p.x)<(.16-.12*(p.z-.36)) and p.y<-.18 and p.z>.34):poly.material_index=1
        # Exportable tapered four-sided hair ribbons with directional combing.
        rng=random.Random(405); fv=[];ff=[]
        for i in range(4400):
            t=math.acos(rng.uniform(-.98,.98));p=rng.uniform(0,2*pi);a=surface(t,p)
            if a.y<-.18 and abs(a.x)<.43 and -.22<a.z<.39:continue
            normal=Vector((a.x/.51**2,a.y/.39**2,a.z/.68**2)).normalized()
            length=rng.uniform(.032,.074);comb=Vector((a.x*.12,.018,-.028 if a.z<.3 else .04))
            tip=a+normal*length+comb;cross=normal.cross(Vector((0,0,1)))
            if cross.length<.1:cross=Vector((1,0,0))
            cross.normalize();w=rng.uniform(.003,.006);base=len(fv)
            for pt in [a-cross*w,a+cross*w,(a+tip)*.5+cross*w*.5,tip,(a+tip)*.5-cross*w*.5]:fv.append(tuple(c+pt*s))
            ff.extend([(base,base+1,base+2,base+4),(base+4,base+2,base+3)])
        hairs=self.mesh('combed tapered fur strands',fv,ff,fur)
        if style=='blackwhite':
            hairs.data.materials.append(dark)
            for poly in hairs.data.polygons:
                p=Vector((0,0,0))
                for vi in poly.vertices:p+=hairs.data.vertices[vi].co
                p=(p/len(poly.vertices)-c)/s
                if (abs(p.x)>.35 and p.z<.30) or (abs(p.x)<.13 and p.y<-.21 and p.z>.36):poly.material_index=1
        if ears:
            for sign in [-1,1]:
                shape=[(.27,.42),(.43,.48),(.61,.64),(.73,.83),(.79,1.04),(.66,.95),(.51,.80),(.36,.66)]
                if style=='blackwhite':shape=[(.27,.42),(.46,.50),(.58,.70),(.64,.94),(.65,1.20),(.53,1.03),(.40,.83),(.30,.67)]
                front=[P(sign*x,-.045,z) for x,z in shape];back=[P(sign*x,.055,z) for x,z in shape];N=len(shape)
                self.mesh('thick sculpted pointed ear',front+back,[tuple(range(N)),tuple(reversed(range(N,2*N)))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)],fur,.018*s)
                mid=Vector((sum(p[0] for p in shape)/N,sum(p[1] for p in shape)/N))
                insert=[P(sign*(mid.x+(x-mid.x)*.73),-.062,mid.y+(z-mid.y)*.78) for x,z in shape]
                self.mesh('recessed velvet ear insert',insert,[tuple(range(N))],inside)
                self.tube('rounded ear welt',front+[front[0]],.022*s,fur)
        for sign in [-1,1]:
            x=sign*.225
            self.sphere('raised facial socket',P(x,-.315,.17),(.23*s,.11*s,.25*s),cream)
            self.torus('dark rounded eyelid',P(x,-.412,.19),.175*s,.03*s,dark)
            self.sphere('round eye white',P(x,-.435,.19),(.159*s,.073*s,.172*s),cream)
            self.sphere('iris',P(x-sign*.014,-.501,.19),(.092*s,.021*s,.103*s),iris)
            self.sphere('pupil',P(x-sign*.014,-.522,.195),(.059*s,.014*s,.076*s),dark)
            self.sphere('eye glint',P(x-.025,-.536,.23),(.025*s,.008*s,.026*s),cream)
        self.sphere('upper rounded beak',P(0,-.432,-.062),(.12*s,.137*s,.086*s),yellow)
        self.sphere('beak seam shadow',P(0,-.48,-.12),(.106*s,.091*s,.013*s),dark)
        self.sphere('lower rounded beak',P(0,-.442,-.151),(.098*s,.108*s,.051*s),yellow)
        # Sparse crown with combed tuft silhouette.
        for i in range(27):
            x=(i-13)*.009;self.cone('crown tuft',P(x,0,.62),P(x*1.15,.055,.81+rng.random()*.08),.017*s,0,fur,5)
        h=bpy.data.objects.new('Furby head assembly',None);self.collection.objects.link(h);h.parent=self.root;h.location=c
        for o in set(self.collection.objects)-old-{h}:o.parent=h;o.matrix_parent_inverse=h.matrix_basis.inverted()
        return h
    def leg(self,root,knee,foot,style='armored',width=.2):
        a,k,f=map(Vector,(root,knee,foot));w=width
        direction=Vector((k.x-a.x,k.y-a.y,0)).normalized();normal=Vector((0,0,1)).cross(direction).normalized()
        for label,p,r in [('hip',a,w*.65),('knee',k,w*.63)]:
            self.cyl(label+' axle',p-normal*w*.62,p+normal*w*.62,r,self.steel)
            self.torus(label+' bearing',p-normal*w*.65,r*.72,w*.12,self.edge,normal)
            self.bolt(p-normal*w*.75,-normal,w*.18)
        self.cyl('upper structural spar',a,k,w*.33,self.steel)
        def armorbar(p,q,width,depth):
            d=q-p;o=self.box('articulated armor plate',(p+q)*.5,(width,depth,d.length*.43),self.armor,.025);z=d.normalized();x=normal.cross(z).normalized();y=z.cross(x).normalized();o.rotation_euler=Matrix((x,y,z)).transposed().to_euler();return o
        armorbar(a,k,w*.55,w*.42)
        def detailbar(p,q,width,depth):
            d=q-p;z=d.normalized();x=normal.cross(z).normalized();y=z.cross(x).normalized();rot=Matrix((x,y,z)).transposed().to_euler()
            for side in [-1,1]:
                face=(p+q)*.5+y*depth*side
                o=self.box('recessed limb inset',face,(width*.64,.009,d.length*.28),self.steel,.009);o.rotation_euler=rot
                for t in [.18,.50,.82]:
                    loc=p.lerp(q,t)+y*(depth+.014)*side
                    o=self.box('armor transverse seam',loc,(width*.92,.008,.009),self.black,.003);o.rotation_euler=rot
                for t in [.15,.85]:
                    for edge in [-1,1]:self.bolt(p.lerp(q,t)+y*(depth+.02)*side+x*width*.77*edge,y*side,w*.075)
                for t in [.27,.39,.51,.63]:
                    o=self.box('limb inset grille',p.lerp(q,t)+y*(depth+.022)*side,(width*.40,.012,.009),self.edge,.003);o.rotation_euler=rot
        detailbar(a,k,w*.55,w*.425)
        offset=-normal*w*.5;self.cyl('chrome piston rod',a+offset,k+offset,w*.11,self.edge)
        self.cyl('hydraulic cylinder',a.lerp(k,.10)+offset,a.lerp(k,.58)+offset,w*.20,self.steel)
        for t in [.12,.23,.47,.56]:self.torus('hydraulic retaining collar',a.lerp(k,t)+offset,w*.205,w*.035,self.edge,k-a)
        if style=='needle':
            self.cone('needle lower leg',k,f,w*.32,.009,self.edge)
            self.cone('needle collar',k,k.lerp(f,.24),w*.43,w*.32,self.armor)
        elif style=='blade':
            # A continuous bowed crescent in the local radial/vertical leg plane.
            control=k.lerp(f,.5)+direction*.56
            samples=16;verts=[];faces=[];centers=[];thickness=max(.055,w*.4)
            for i in range(samples+1):
                t=i/samples;p=k*(1-t)**2+control*(2*t*(1-t))+f*t*t
                tangent=((control-k)*(2*(1-t))+(f-control)*(2*t)).normalized()
                across=normal.cross(tangent).normalized()
                width=(.18-.08*t)*(1-t**4)
                if i==samples:width=.003
                centers.append(p-normal*(thickness*.5+.005))
                for depth in [-.5,.5]:
                    for side in [-1,1]:verts.append(tuple(p+across*(side*width*.5)+normal*(depth*thickness)))
            for i in range(samples):
                a0=i*4;b0=(i+1)*4
                faces.extend([(a0,a0+1,b0+1,b0),(a0+2,b0+2,b0+3,a0+3),(a0,b0,b0+2,a0+2),(a0+1,a0+3,b0+3,b0+1)])
            faces.extend([(0,2,3,1),(samples*4,samples*4+1,samples*4+3,samples*4+2)])
            self.mesh('continuous swept crescent claw',verts,faces,self.armor,.007)
            self.tube('crescent machined central ridge',centers,.009,self.edge)
        else:
            self.cyl('lower skeleton',k,f,w*.27,self.steel);armorbar(k,k.lerp(f,.85),w*.58,w*.44);detailbar(k,k.lerp(f,.85),w*.58,w*.445)
            self.cyl('lower chrome piston',k+offset,f+offset,w*.12,self.edge)
            if style=='armored_pointed':
                self.cone('tapered armored spear toe',k.lerp(f,.73),f,w*.41,.004,self.edge,4)
            else:self.box('flat footplate',(f.x,f.y,.045),(w*.66,w*.70,.045),self.edge,.013)
            for t in [.25,.68]:self.bolt(k.lerp(f,t)-normal*w*.46,-normal,w*.14)
        return None
    def barrel(self,start,end,r=.1,spiked=False):
        a,b=Vector(start),Vector(end);d=b-a;n=d.normalized()
        self.cyl('long barrel',a,b,r,self.steel)
        for i in range(19):self.torus('barrel rib',a+d*i/20,r*1.05,r*.17,self.edge,axis=n)
        self.cyl('breech',a,a+d*.18,r*1.65,self.armor)
        self.torus('muzzle ring',b,r,r*.22,self.edge,axis=n)
        self.cyl('dark muzzle bore',b+n*.003,b+n*.008,r*.75,self.black)
        if spiked:
            q=n.to_track_quat('Z','Y')
            for i in range(9):
                for j in range(4):
                    radial=q@Vector((cos(j*pi/2),sin(j*pi/2),0));p=a+d*(.2+.7*i/9)+radial*r
                    self.cone('barrel spine',p,p+radial*r*1.5+n*r*.4,r*.29,0,self.edge,8)
    def star(self,center,size,mat,axis=(0,-1,0)):
        c=Vector(center);q=Vector(axis).to_track_quat('Z','Y');v=[]
        for i in range(10):t=pi/2+i*pi/5;r=size if i%2==0 else size*.43;v.append(c+q@Vector((r*cos(t),r*sin(t),0)))
        return self.panel('five point star',v,mat,.014)

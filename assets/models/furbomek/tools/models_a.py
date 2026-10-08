from swarm_geometry import Builder
from math import sin,cos,pi
from mathutils import Vector

def metadata(b,n,source):
    b.root['model_id']=n;b.root['canonical_reference']=source;b.root['interpretation']='Reference-derived miniature; not an exact reconstruction or measured scale.'
    return b

def sixlegs(b,style='armored',height=1.1,spread=1.4,width=.2):
    for side in [-1,1]:
        for row in [-1,0,1]:
            b.leg((side*.49,row*.38,height),(side*(.91 if row else 1.12),row*.65,height+.10),(side*spread,row*.98,.04),style,width)

def ringbody(b,z=1.1):
    b.cyl('central round reactor',(0,0,z-.23),(0,0,z+.14),.63,b.steel,48)
    for level in [-.19,.08]:b.torus('continuous chassis flange',(0,0,z+level),.64,.055,b.edge,(0,0,1))
    for i in range(12):
        a=2*pi*i/12;c=Vector((.61*cos(a),.61*sin(a),z));o=b.box('separate riveted torso segment',c,(.16,.065,.15),b.armor,.018);o.rotation_euler.z=a-pi/2
        for dz in [-.095,.095]:b.bolt((.685*cos(a),.685*sin(a),z+dz),(cos(a),sin(a),0),.022)
    for x in [-.23,0,.23]:
        b.cyl('exposed lower actuator',(x,0,z-.46),(x,0,z-.23),.075,b.edge)
        b.box('lower servo',(x,-.11,z-.35),(.083,.12,.095),b.steel)

def helmet(b,z,skull=False):
    pale=b.mat('cast porcelain mask',(.76,.75,.65),.2,.39)
    b.sphere('rounded panel helmet',(0,0,z),(.48,.43,.47),b.steel)
    # Plate strips across dome leave a broad open front for expression.
    for i in range(10):
        a=2*pi*i/10
        if sin(a)<-.5:continue
        for j in range(6):
            t0=.18+j*.42;t1=t0+.38;vs=[]
            for t,p in [(t0,a-.27),(t0,a+.27),(t1,a+.27),(t1,a-.27)]:vs.append((.49*sin(t)*cos(p),.44*sin(t)*sin(p),z+.48*cos(t)))
            b.panel('helmet dome segmented panel',vs,b.armor,.018)
            t=(t0+t1)*.5;b.bolt((.503*sin(t)*cos(a),.453*sin(t)*sin(a),z+.49*cos(t)),(sin(t)*cos(a),sin(t)*sin(a),cos(t)),.016)
    b.torus('helmet equatorial band',(0,0,z-.03),.455,.045,b.edge,(0,0,1))
    for s in [-1,1]:
        b.panel('front helmet temple armor',[(s*.25,-.33,z+.32),(s*.39,-.28,z+.25),(s*.43,-.25,z-.18),(s*.29,-.34,z-.28)],b.armor,.032)
        for j in range(4):
            b.box('helmet side vent recess',(s*.472,.05+(j-1.5)*.055,z-.11),(.012,.018,.085),b.black,.004)
        for zz in [z+.22,z-.23]:b.bolt((s*.35,-.335,zz),(0,-1,0),.02)
    b.tube('mask brow raised contour',[(-.29,-.383,z+.24),(-.19,-.41,z+.34),(0,-.421,z+.37),(.19,-.41,z+.34),(.29,-.383,z+.24)],.025,b.edge)
    b.sphere('inset expressive face',(0,-.375,z-.03),(.31,.10,.35),pale)
    for x in [-.137,.137]:
        b.torus('face eye rim',(x,-.474,z+.095),.083,.018,b.edge)
        b.sphere('round black eye',(x,-.489,z+.095),(.073,.025,.084),b.black)
        if not skull:b.sphere('eye sparkle',(x-.016,-.511,z+.124),(.017,.006,.02),pale)
    if skull:
        b.sphere('skull nasal hollow',(0,-.486,z-.038),(.052,.022,.044),b.black)
        b.sphere('skull jaw shadow',(0,-.45,z-.205),(.16,.041,.096),b.black)
        for i in range(7):b.box('individual skull tooth',((i-3)*.04,-.486,z-.184+abs(i-3)*.009),(.016,.025,.047),pale,.009)
        for s in [-1,1]:
            b.sphere('flared skull cheek',(s*.225,-.426,z-.115),(.084,.055,.10),pale)
            b.box('side helmet equipment',(s*.46,.015,z-.02),(.07,.16,.18),b.armor)
            b.cyl('side helmet hinge',(s*.51,-.1,z),(s*.51,.13,z),.082,b.edge)
    else:
        b.sphere('open smiling mouth',(0,-.474,z-.12),(.14,.026,.106),b.black)
        b.sphere('smile lower lip',(0,-.492,z-.165),(.10,.015,.035),pale)
        b.sphere('small nose',(0,-.503,z+.005),(.048,.041,.048),pale)
        for s in [-1,1]:b.sphere('rounded smiling cheek',(s*.18,-.473,z-.063),(.063,.029,.055),pale)
    for s in [-1,1]:
        for zz in [z-.19,z+.24]:b.bolt((s*.32,-.366,zz),(0,-1,0),.025)
    b.box('helmet crown hatch',(0,0,z+.465),(.15,.14,.026),b.armor)
    b.box('crown hatch handle',(0,0,z+.51),(.065,.022,.02),b.edge)

def build_01():
    b=Builder('01 Armored Smile Hexapod');b.armor=b.mat('pale warm enamel',(.57,.56,.48),.4)
    sixlegs(b,'armored',1.02,1.40,.235);ringbody(b,1.17);helmet(b,1.82)
    for s in [-1,1]:
        b.barrel((s*.55,-.10,1.55),(s*.64,-.64,1.55),.04)
        b.tube('underbody cable',[(s*.30,-.15,.95),(s*.36,-.35,.81),(s*.16,-.39,.69)],.025,b.black)
    return metadata(b,1,'01_armored_smile.png')

def build_02():
    b=Builder('02 Fur Needle Scout')
    for side in [-1,1]:
        for row in [-1,0,1]:b.leg((side*.27,row*.2,.78),(side*.59,row*.40,.9),(side*.97,row*.72,.025),'needle',.105)
    for z in [.61,.80]:
        b.box('stacked rectangular belly',(0,0,z),(.29,.23,.085),b.armor)
        b.box('belly inset face',(0,-.243,z),(.21,.014,.051),b.edge)
        for x in [-.23,.23]:b.bolt((x,-.26,z),(0,-1,0),.021)
    b.head((0,0,1.57),.86,color=(.86,.86,.81),ear_inner=(.10,.12,.12),style='blackwhite')
    return metadata(b,2,'02_fur_scout.png')

def hull(b,length=1.0,z=1.25):
    v=[(-.55,-length,z-.22),(.55,-length,z-.22),(.64,.65,z-.22),(-.64,.65,z-.22),(-.42,-length-.12,z+.13),(.42,-length-.12,z+.13),(.55,.57,z+.24),(-.55,.57,z+.24)]
    b.mesh('angular vehicle hull',v,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7),(3,2,1,0)],b.steel,.035)
    b.panel('sloped upper armor',[(-.39,-length-.11,z+.153),(.39,-length-.11,z+.153),(.51,.42,z+.265),(-.51,.42,z+.265)],b.armor,.025)
    def topz(y):return z+.153+(y+length+.11)/(.42+length+.11)*.112
    for s in [-1,1]:
        pts=[(s*.045,-length+.12,topz(-length+.12)+.008),(s*.34,-length+.12,topz(-length+.12)+.008),(s*.42,-.05,topz(-.05)+.008),(s*.045,-.05,topz(-.05)+.008)]
        b.panel('bolted upper front hatch',pts,b.edge,.025)
        for x,y,zz in pts:b.bolt((x,y,zz+.021),(0,0,1),.021)
        b.tube('upper hull panel joint',[(s*.03,-length-.08,topz(-length-.08)+.008),(s*.03,.40,topz(.4)+.008)],.009,b.black)
    for s in [-1,1]:
        b.panel('angled side armor',[(s*.57,-length+.06,z-.19),(s*.66,.55,z-.19),(s*.56,.54,z+.19),(s*.46,-length+.02,z+.10)],b.armor,.025)
        for y in [-.62,-.23,.21,.51]:
            b.bolt((s*.62,y,z-.1),(s,0,0),.029)
        b.box('side inset access plate',(s*.641,-.26,z-.018),(.018,.19,.10),b.steel,.014)
        for y in [-.40,-.12]:
            for dz in [-.065,.065]:b.bolt((s*.664,y,z-.018+dz),(s,0,0),.018)
        b.tube('side armor division line',[(s*.604,-length+.09,z-.07),(s*.665,.48,z-.07)],.011,b.black)
        for i in range(5):b.box('side cooling vent',(s*.655,.2+i*.058,z+.03),(.014,.014,.076),b.black,.005)
    return b

def build_03():
    b=Builder('03 Skull Sentinel');sixlegs(b,'armored_pointed',1.03,1.48,.21);ringbody(b,1.10);helmet(b,1.76,True)
    for s in [-1,1]:
        b.barrel((s*.47,.17,1.39),(s*.66,.19,1.98),.065)
        b.tube('hanging mechanical hose',[(s*.3,-.1,1.15),(s*.4,-.28,.85),(s*.17,-.34,.77)],.024,b.black)
    return metadata(b,3,'03_skull_sentinel.png')

def build_04():
    b=Builder('04 Cannon Quadruped');hull(b,.8,1.22)
    for s in [-1,1]:
        for row in [-1,1]:
            b.leg((s*.5,row*.43,1.15),(s*.92,row*.68,1.19),(s*1.35,row*1.04,.06),'armored',.27)
            for i in range(5):b.box('foot traction rib',(s*1.35,row*1.04-.14+i*.06,.108),(.16,.012,.012),b.steel,.003)
    b.head((0,-.07,1.92),.57,color=(.86,.85,.79),ears=False,style='blackwhite')
    b.barrel((0,-.62,1.22),(0,-2.6,1.22),.083)
    b.cyl('rear horizontal capsule',(-.52,.37,1.89),(.52,.37,1.89),.19,b.armor)
    for s in [-1,1]:
        b.sphere('capsule rounded end',(s*.52,.37,1.89),(.09,.19,.19),b.edge)
        b.box('pod bracket',(s*.31,.37,1.59),(.06,.1,.16),b.steel)
        for x in [s*.18,s*.39]:
            b.cyl('capsule circular access port',(x,.188,1.90),(x,.169,1.90),.069,b.black)
            b.torus('capsule access port lip',(x,.164,1.90),.070,.014,b.edge)
        b.torus('capsule service collar',(s*.47,.37,1.89),.195,.018,b.steel,(1,0,0))
    return metadata(b,4,'04_cannon_walker.png')

def build_09():
    b=Builder('09 Video Armored Crawler');hull(b,1.15,1.15)
    for s in [-1,1]:
        for row in [-1,0,1]:b.leg((s*.48,row*.53,1.02),(s*.88,row*.67,.91),(s*1.40,row*.96,.025),'needle',.22)
    b.head((0,-.41,1.72),.39,color=(.81,.81,.77),ears=False,beak=(.53,.54,.48),style='blackwhite')
    for s in [-1,1]:
        b.box('rear utility crate',(s*.29,.65,1.24),(.25,.25,.21),b.armor)
        for j in range(5):b.box('rear horizontal grille',(s*.29,.908,1.15+j*.044),(.19,.015,.012),b.black,.003)
        b.tube('rear antenna stalk',[(s*.43,.61,1.47),(s*.47,.67,1.82),(s*.51,.65,2.02)],.018,b.steel)
        b.box('antenna terminal',(s*.51,.65,2.03),(.044,.035,.065),b.edge)
        b.cyl('round side access hatch',(s*.60,-.53,1.17),(s*.64,-.53,1.17),.108,b.steel)
        b.torus('access hatch rim',(s*.65,-.53,1.17),.105,.014,b.edge,(1,0,0))
    return metadata(b,9,'video_04.jpg')

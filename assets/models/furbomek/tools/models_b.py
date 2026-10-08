"""Reference-specific tracked graft tank and three distinct blue blade walkers.

All geometry is authored from the supplied reference sheets, front along -Y.
"""
import math
from swarm_geometry import Builder


def _materials(b):
    return {
        'steel': b.mat('satin pale alloy', (.48, .51, .51), metal=.72, rough=.33),
        'edge': b.mat('machined edge', (.69, .72, .70), metal=.8, rough=.27),
        'dark': b.mat('recessed gunmetal', (.055, .069, .075), metal=.72, rough=.44),
        'rubber': b.mat('track rubber', (.027, .033, .035), rough=.82),
        'red': b.mat('vermilion enamel', (.68, .018, .025), metal=.12, rough=.34),
        'ivory': b.mat('warm pale paws', (.88, .88, .78), rough=.76),
    }


def _metadata(b, source, features):
    for obj in (b.root, b.collection):
        obj['source_reference'] = source
        obj['distinctive_features'] = features
        obj['forward_axis'] = '-Y'
    return b


def _plate(b, name, x, y, z, w, h, m):
    b.box(name, (x, y, z), (w, .027, h), m['steel'], bevel=.022)
    for sx in (-1, 1):
        for sz in (-1, 1):
            b.bolt((x+sx*(w-.045), y-.032, z+sz*(h-.045)), (0,-1,0), .022)


def _claws(b, m, x=.36, y=-.62, z=.86, reach=.4):
    for s in (-1, 1):
        a=(s*x,y,z); c=(s*(x+.05),y-.17,z-.21); d=(s*(x+.04),y-reach,z-.30)
        b.cyl('claw shoulder axle', (a[0]-.065,a[1],a[2]), (a[0]+.065,a[1],a[2]), .075,m['dark'])
        b.cyl('pincer upper linkage',a,c,.047,m['steel'])
        b.cyl('pincer chrome piston', (s*(x-.04),y,z-.035), c,.022,m['edge'])
        b.cyl('pincer forearm',c,d,.039,m['steel'])
        b.sphere('pincer wrist',d,(.065,.055,.055),m['dark'])
        for t in (-1,1):
            e=(d[0]+t*.10,d[1]-.09,d[2]-.025)
            f=(d[0]+t*.045,d[1]-.20,d[2]-.09)
            b.cone('articulated grasp finger',d,e,.034,.023,m['steel'])
            b.cone('curved grasp finger tip',e,f,.024,.004,m['edge'])


def _six_blades(b,m,red=False):
    for s in (-1,1):
        for i,y in enumerate((-.43, .05, .5)):
            a=(s*.57,y,.9)
            knee=(s*(1.00 if i!=1 else 1.17),y+(-.18 if i==0 else .10),1.05)
            foot=(s*(1.25 if i!=1 else 1.42),y+(-.38 if i==0 else .29),.025)
            b.leg(a,knee,foot,style='blade',width=.145)
            if red:
                b.tube('red hydraulic hose',[(s*.61,y+.035,.97),(s*.73,y+.06,.65),(s*.9,y+.03,.60),(knee[0],knee[1],.94)],.023,m['red'])


def _side_gun(b,m,s,z=1.54,twin=False,x_offset=.70,barrel_length=.60):
    x=s*x_offset
    b.box('gun mounting cheek block',(x,-.24,z),(.14,.19,.14),m['steel'])
    _plate(b,'gun mount front flange',x,-.435,z,.145,.145,m)
    levels=(-.065,.065) if twin else (0,)
    for dz in levels:
        b.barrel((x,-.44,z+dz),(x,-.44-barrel_length,z+dz),r=.058 if twin else .074)
    b.cyl('mount swivel hub',(x+s*.06,-.2,z),(x+s*.20,-.2,z),.12,m['dark'])
    b.bolt((x+s*.21,-.2,z),(s,0,0),.035)


def _box_chassis(b,m,round_badge=False):
    b.box('rectangular undercarriage',(0,.08,.98),(.66,.53,.25),m['dark'],bevel=.08)
    b.box('upper chassis lip',(0,.08,1.225),(.72,.58,.048),m['edge'])
    b.box('lower chassis lip',(0,.08,.77),(.61,.51,.035),m['steel'])
    _plate(b,'front armored service door',0,-.466,1.0,.38,.205,m)
    if round_badge:
        b.cyl('circular star escutcheon',(0,-.493,1.0),(0,-.535,1.0),.163,m['edge'])
        b.torus('escutcheon milled rim',(0,-.545,1.0),.143,.016,m['dark'])
        b.star((0,-.559,1.0),.122,m['red'])
    else:
        b.star((0,-.508,1.0),.16,m['red'])
    for s in (-1,1):
        b.box('side armored cover',(s*.676,.12,1.0),(.024,.36,.175),m['steel'])
        for y in (-.15,.38):
            for z in (.87,1.13): b.bolt((s*.707,y,z),(s,0,0),.027)
        for y in (.05,.12,.19,.26):
            b.box('rear side vent slot',(s*.705,y,1.04),(.011,.017,.082),m['dark'],bevel=.006)
    for i in range(7):
        b.box('rear grille louver',(-.43+i*.14,.629,.98),(.035,.015,.14),m['steel'],bevel=.008)


def build_06():
    b=Builder('06_blue_orange_hydraulic'); m=_materials(b)
    b.cyl('lower round mechanism drum',(0,.08,.72),(0,.08,1.01),.60,m['dark'],verts=12)
    b.cone('faceted flaring armored steel skirt',(0,.08,1.0),(0,.08,1.34),.78,.56,m['steel'],verts=12)
    b.cyl('skirt lower rolled rim',(0,.08,.98),(0,.08,1.025),.785,m['edge'],verts=12)
    for i in range(12):
        a=2*math.pi*i/12
        x,y=.69*math.cos(a),.08+.69*math.sin(a)
        b.bolt((x,y,1.12),(math.cos(a),math.sin(a),.6),.025)
        b.cyl('skirt panel seam',(.775*math.cos(a),.08+.775*math.sin(a),1.027),(.56*math.cos(a),.08+.56*math.sin(a),1.34),.006,m['dark'],verts=8)
    _six_blades(b,m)
    h=b.head((0,.04,1.78),scale=.90,color=(.025,.48,.63),ear_inner=(.95,.34,.065),beak=(.98,.61,.025)); h.scale.x=1.22
    for s in (-1,1): _side_gun(b,m,s,z=1.62,x_offset=.65)
    b.cyl('front circular access gauge',(0,-.65,1.16),(0,-.69,1.16),.105,m['edge'])
    b.torus('gauge bezel',(0,-.699,1.16),.075,.014,m['dark'])
    b.cyl('gauge diagonal pointer',(-.025,-.717,1.14),(.027,-.717,1.194),.009,m['dark'])
    _claws(b,m,x=.25,y=-.53,z=.83,reach=.28)
    return _metadata(b,'06_blue_orange.png','cyan fur; orange inner ears; yellow beak; single lateral barrels; faceted skirt; six blade legs; paired tiny pincers')


def build_07():
    b=Builder('07_navy_red_star'); m=_materials(b)
    _box_chassis(b,m)
    _six_blades(b,m,red=True)
    h=b.head((0,.04,1.81),scale=.91,color=(.006,.025,.08),ear_inner=(.76,.014,.029),beak=(.68,.70,.67)); h.scale.x=1.22
    for s in (-1,1):
        _side_gun(b,m,s,z=1.47)
        b.box('ribbed front equipment backing',(s*.48,-.56,.83),(.115,.12,.19),m['dark'])
        for j in range(7):
            b.box('equipment transverse cooling rib',(s*.48,-.691,.674+j*.048),(.123,.027,.016),m['edge'],bevel=.008)
        b.box('upright side servo housing',(s*.68,-.22,1.2),(.115,.12,.19),m['steel'])
        b.tube('red upper supply loop',[(s*.7,.03,1.57),(s*.83,.15,1.44),(s*.80,.36,1.17),(s*.70,.30,.86)],.026,m['red'])
        b.cyl('rear barrel module',(s*.55,.54,1.35),(s*.55,.94,1.35),.067,m['dark'])
        for j in range(5):
            b.torus('rear module cooling ring',(s*.55,.6+j*.055,1.35),.074,.012,m['steel'])
    return _metadata(b,'07_navy_red.png','navy fur; red ears; silver beak; square front red star plate; two ribbed front equipment blocks; six blade legs; red hoses; side barrel modules')


def build_08():
    b=Builder('08_blue_red_cheek_gunner'); m=_materials(b)
    _box_chassis(b,m,round_badge=True)
    _six_blades(b,m,red=True)
    h=b.head((0,.04,1.84),scale=.93,color=(.012,.48,.69),ear_inner=(.81,.016,.032),beak=(.73,.76,.70)); h.scale.x=1.22
    for s in (-1,1):
        _side_gun(b,m,s,z=1.90,twin=True,x_offset=.63,barrel_length=.40)
        for dx in (-.065,.065):
            b.sphere('little white forepaw',(s*.37+dx,-.43,1.30),(.09,.15,.075),m['ivory'])
        b.tube('upper bright red hydraulic feed',[(s*.53,.26,1.23),(s*.79,.24,1.17),(s*.77,-.14,.97)],.027,m['red'])
    b.box('cudgel side saddle',( .78,.28,1.03),(.17,.22,.13),m['steel'])
    b.cyl('cudgel power actuator',(.88,.46,1.07),(.88,-.22,1.07),.14,m['dark'])
    b.barrel((.88,-.24,1.07),(.88,-1.80,1.07),r=.105,spiked=True)
    b.tube('cudgel hooked distal tip',[(.88,-1.80,1.07),(.88,-1.94,1.045),(.88,-2.00,1.12)],.026,m['edge'])
    return _metadata(b,'08_blue_red.png','bright cyan fur; red ears; silver split beak; four cheek gun barrels; white paws; circular star badge; six blade legs; red hydraulics; long spiked side cudgel')


def _tank_track(b,m,s):
    x=s*1.035; radius=.405; zc=.49; straight=1.01
    for i in range(5):
        y=-.79+i*.395
        b.cyl('rubber road wheel',(x-.22,y,.44),(x+.22,y,.44),.29,m['rubber'])
        b.cyl('alloy roadwheel outer disc',(x+s*.23,y,.44),(x+s*.255,y,.44),.238,m['steel'])
        b.cyl('roadwheel bearing',(x+s*.254,y,.44),(x+s*.285,y,.44),.087,m['dark'])
        b.bolt((x+s*.29,y,.44),(s,0,0),.046)
        for j in range(6):
            a=math.tau*j/6
            b.bolt((x+s*.274,y+math.cos(a)*.163,.44+math.sin(a)*.163),(s,0,0),.022)
    for y in (-straight,straight):
        b.cyl('end toothed sprocket',(x-.20,y,zc),(x+.20,y,zc),.33,m['dark'])
        b.cyl('sprocket outer plate',(x+s*.21,y,zc),(x+s*.255,y,zc),.265,m['edge'])
        b.cyl('sprocket hub',(x+s*.257,y,zc),(x+s*.30,y,zc),.12,m['steel'])
        for j in range(12):
            a=math.tau*j/12
            b.box('sprocket tooth',(x,y+math.cos(a)*.342,zc+math.sin(a)*.342),(.19,.045,.04),m['steel'],bevel=.009,rotation=(a,0,0))
            b.bolt((x+s*.274,y+math.cos(a)*.203,zc+math.sin(a)*.203),(s,0,0),.022)
    points=[]
    # A closed stadium perimeter, each independently hinged shoe tangent to travel.
    for j in range(16): points.append((-straight+2*straight*j/16,zc+radius,0))
    for j in range(14):
        a=math.pi/2-math.pi*j/14
        points.append((straight+radius*math.cos(a),zc+radius*math.sin(a),a-math.pi/2))
    for j in range(16): points.append((straight-2*straight*j/16,zc-radius,math.pi))
    for j in range(14):
        a=-math.pi/2-math.pi*j/14
        points.append((-straight+radius*math.cos(a),zc+radius*math.sin(a),a-math.pi/2))
    for i,(y,z,a) in enumerate(points):
        b.box('linked tread shoe %02d'%i,(x,y,z),(.29,.057,.035),m['dark'],bevel=.010,rotation=(a,0,0))
        b.box('raised transverse tread cleat %02d'%i,(x,y-.048*math.sin(a),z+.048*math.cos(a)),(.27,.022,.020),m['steel'],bevel=.007,rotation=(a,0,0))
        b.cyl('track hinge pin',(x-.32,y,z),(x+.32,y,z),.025,m['edge'],verts=12)


def build_05():
    b=Builder('05_tracked_graft_tank'); m=_materials(b)
    for s in (-1,1): _tank_track(b,m,s)
    b.box('lower armored tub',(0,.0,.72),(.79,1.13,.29),m['dark'],bevel=.10)
    verts=[(-.87,-1.28,.82),(.87,-1.28,.82),(.87,1.18,.82),(-.87,1.18,.82),(-.68,-.82,1.17),(.68,-.82,1.17),(.74,.97,1.17),(-.74,.97,1.17)]
    b.mesh('sloping upper hull',verts,[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],m['steel'],bevel=.035)
    for s in (-1,1):
        b.box('track fender',(s*1.025,0,.99),(.32,1.37,.045),m['steel'],bevel=.025)
        for y in (-1.1,-.6,0,.6,1.1):
            b.bolt((s*1.16,y,1.042),(0,0,1),.031)
        b.panel('front glacis inset',[(s*.12,-1.274,.855),(s*.69,-1.274,.855),(s*.56,-.837,1.176),(s*.12,-.837,1.176)],m['edge'],depth=.017)
        for y in (.63,.79,.95): b.box('rear exhaust armored ribs',(s*.43,y,1.21),(.20,.043,.035),m['dark'],bevel=.01)
        b.box('rear equipment case',(s*.68,.92,1.28),(.16,.22,.12),m['steel'])
        for y in (-.65,.05,.68): b.box('fender panel seam',(s*1.025,y,1.039),(.29,.008,.006),m['dark'],bevel=0)
    b.cyl('turret race',(0,.07,1.16),(0,.07,1.27),.69,m['dark'])
    b.cyl('turret lower rolled ring',(0,.07,1.255),(0,.07,1.3),.735,m['edge'])
    b.cyl('round riveted turret',(0,.07,1.30),(0,.07,1.77),.695,m['steel'],verts=48)
    b.cone('turret sloped roof',(0,.07,1.77),(0,.07,1.84),.69,.57,m['steel'])
    for i in range(20):
        a=math.tau*i/20
        for z in (1.34,1.73): b.bolt((.704*math.cos(a),.07+.704*math.sin(a),z),(math.cos(a),math.sin(a),0),.025)
    for s in (-1,1):
        b.box('turret side service hatch',(s*.693,.13,1.54),(.025,.21,.16),m['edge'])
        b.cyl('hatch handle',(s*.741,.04,1.51),(s*.741,.21,1.51),.023,m['dark'])
    b.cyl('cannon armored mantlet',(0,-.55,1.54),(0,-.82,1.54),.24,m['dark'])
    b.torus('mantlet rim',(0,-.83,1.54),.204,.029,m['edge'])
    b.barrel((0,-.84,1.54),(0,-2.53,1.54),r=.109,spiked=True)
    # Two substantial manipulator arms stand ahead of the tread envelope.
    # Unlike the little walker pincers, these have long plated forearms.
    from mathutils import Vector
    for s in (-1,1):
        shoulder=Vector((s*1.12,-1.35,1.015))
        elbow=Vector((s*1.19,-1.60,.76))
        wrist=Vector((s*1.21,-1.67,.35))
        b.box('front claw shoulder mounting bracket',(s*1.12,-1.29,1.015),(.13,.12,.10),m['dark'])
        for label,p,r in [('shoulder',shoulder,.102),('elbow',elbow,.084),('wrist',wrist,.064)]:
            b.cyl('manipulator '+label+' hinge',p+Vector((-.11,0,0)),p+Vector((.11,0,0)),r,m['dark'])
            b.bolt(p+Vector((s*.12,0,0)),(s,0,0),r*.45)
        for label,p,q,w in [('upper arm',shoulder,elbow,.082),('long forearm',elbow,wrist,.072)]:
            b.cyl('manipulator '+label+' structural shaft',p,q,.045,m['dark'])
            obj=b.box('manipulator '+label+' armor',(p+q)*.5,(w,.044,(q-p).length*.43),m['steel'],bevel=.016)
            obj.rotation_euler=(q-p).to_track_quat('Z','Y').to_euler()
            off=Vector((s*.055,-.067,0))
            b.cyl('manipulator hydraulic piston',p+off,q+off,.018,m['edge'])
            b.cyl('manipulator hydraulic jacket',p+off,p.lerp(q,.50)+off,.030,m['dark'])
        b.sphere('manipulator palm',wrist,(.10,.075,.055),m['steel'])
        for t in (-1,1):
            knuckle=wrist+Vector((t*.125,-.09,-.025))
            tip=wrist+Vector((t*.055,-.18,-.10))
            b.cone('tank grasp finger',wrist,knuckle,.039,.026,m['steel'])
            b.cone('tank pointed fingertip',knuckle,tip,.026,.006,m['edge'])
        b.box('rear equipment lid',(s*.68,.92,1.408),(.145,.205,.017),m['edge'],bevel=.01)
        for dx in (-.105,.105):
            for dy in (-.16,.16): b.bolt((s*.68+dx,.92+dy,1.43),(0,0,1),.018)
    b.cyl('graft hatch pedestal',(0,.22,1.83),(0,.22,1.89),.31,m['dark'])
    b.head((0,.22,2.10),scale=.41,color=(.78,.80,.73),ear_inner=(.32,.33,.30),beak=(.65,.64,.52))
    return _metadata(b,'05_tracked_tank.png','twin continuous linked tracks; five road wheels each; end sprockets; sloped hull; round riveted turret; long spiked cannon; two articulated claw arms; small graft Furby head')

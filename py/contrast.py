#! /usr/bin/env python3

# Print examples of colors with "high" contrast compared to a given
# list of background and foreground colors.

# Doesn't work super great.
# Correlation between contrast and readability is meh.  Would probably be better to just sweep and print some examples.

steps=20000
# luminance max / luminance min
# is ~contrast
conThresh=1.8

foregrounds=[0x839496,
             0x657b83,
             0xeee8d5]
backgrounds=[0x002b36]

def decToRGB(dec):
    r=dec//(2**16)
    g=( dec//(2**8) ) % ( 2**8 )
    b=dec % ( 2**8 )
    return(r,g,b)

def lum(rgb):
    (r,g,b)=decToRGB(rgb)
    #print(f"rgb {rgb:0x} r {r:0x} g {g:0x} b {b:0x}")
    gamma=2.2
    return (0.2126 * ( r ** gamma )
          + 0.7152 * ( g ** gamma )
          + 0.0722 * ( b ** gamma ))

def cont(lum1, lum2):
    if lum2 != 0 and lum1 != 0:
        contrast=lum1/lum2
    else:
        return 0
    if contrast < 1 :
        contrast = 1/contrast
    return contrast

def cprint(fore,back):
    (fr,fg,fb)=decToRGB(fore)
    (br,bg,bb)=decToRGB(back)
#    print(f"cprint fore {hex(fore)} fr {hex(fr)} fg {hex(fg)}  fb {hex(fb)} back {hex(back)} br {hex(br)} bg {hex(bg)}  bb {hex(bb)}")
#    print(f";{fr};{fg};{fb}  {br};{bg};{bb}")
    print(f"{cont(lum(fore),lum(back)):6.2f} cont : fore 0x{int(fore):06x} back 0x{int(back):06x}   \033[38;2;{fr};{fg};{fb}m\033[48;2;{br};{bg};{bb}mthis is the     sample text\033[0m  ", end="")
#    print(f"\033[38;2;255;0;0m[48;2;{br};{bg};{bb}mthis is the     sample text\033[0m")

#print(f"\033[38;2;240;100;200m\033[48;2;200;255;50mHello World!\033[0m")
#print(f"\033[38;2;255;101;101m\033[48;2;0;0;0mthis is the     sample text\033[0m")
#exit(1)

lums={}
for color in foregrounds + backgrounds :
    lums[color]=lum(color)
    #print(f"color {color} lum {lums}")

for color in range(0,0xFFFFFF,0xFFFFFF//steps) :
    #print("checking "+hex(color))
    mylum=lum(color)
    minCont=1000
    for fore in foregrounds :
        contrast=cont(lums[fore], lum(color))
        if contrast < minCont :
            minCont = contrast
    for back in backgrounds :
        contrast=cont(lum(color), lums[back])
        if contrast < minCont :
            minCont = contrast
    if minCont > conThresh :
        print(f"{minCont:6.2f} minCont : ", end="")
        for fore in foregrounds :
            #print(f"fore {hex(fore)} color {hex(color)}")
            cprint(fore, color)
#            print("test")
#            cprint(int(0xFF0000), int(0x0))
        #print(".")
        for back in backgrounds :
            #print(f"color {hex(color)} back {hex(back)}")
            cprint(color, back)
        print("")
        #print("--")

#print(f"lum 10 10 10 {lum(0xabcdef)}")
#print(f"\033[38;2;10;10;10m\033[0m\033[48;2;200;200;200mtext\033[0m")


print("")
print("")
print("")
color=0x356900
for fore in foregrounds :
    print(f"fore {hex(fore)} color {hex(color)} cont {cont(lum(fore),lum(color))}")
    cprint(fore, color)
    #            print("test")
    #            cprint(int(0xFF0000), int(0x0))
    print(".")
for back in backgrounds :
    print(f"color {hex(color)} back {hex(back)} cont {cont(lum(back),lum(color))}")
    cprint(color, back)


# color2 is the
#    background for ncdu, contrast with base0 base00 base2
#    foreground for git diff +, contrast with background base03
# 
# iterate by N over the RGB range
# have a contrast min
# show examples for all colors with enough contrast
# 
# 
# for i in {0..15}; do printf "\e[48;5;${i}m color${i} \e[0m\n";done

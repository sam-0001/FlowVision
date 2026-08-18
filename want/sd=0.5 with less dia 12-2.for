      program cylinder_bundle
***************************************************
*	use this program to simulate flow through	*
*	9 heated square cylinders
*   Edited by Mayur YP 		        *
***************************************************
c
      
c
c.....parameters
c
c.....grid size in x- and y-dimension
c
      integer  lx,ly,ll,iter,x,y,t0,t,restart,z

c	  restart = 0 means fresh computations are being done.  restart = 1 means program is being restared after computaions are already done for few time steps.

      integer  dia,n_cyl,save_para,sav_para1,restart_para

c 	save_para and save_para1 saves two set of files required for restarting the program. Two sets are stored just as precaution because electricity may gp off
c 	while one set is being writeen.

c	 restart_para = 0  restarts from node.dat and  restart_para = 1 restarts from node1.dat.  By opening cd signals file, u can know how many steps has already been comput
c	  ed. If time 20000*n > time > 20000*n+10000 then start from restart_para = 0, else from 1.

      real*8   space
      integer anb_para,anb_switch,period

c    anb_para = no of frames in one period
c    anb_switch = 0 means normal computations for u,v and p are to be done,  =1 means frames are to be captured

      integer clsave_para,anbsave_para

c     anbsave_para = no. of timesteps after which anb903 file is to be saved
c     clsave_para = no. of timesteps after which cl and cd signals are to be saved. Here after 10 time steps they are saved to save hard-disk space. Also this means
c	that shedding etc we will get will always be multiple of 10.

        integer yl
        real*8 sd
      parameter(dia=12,n_cyl=6,space=19.0d0,restart=0,save_para=20000)
      parameter (sd=0.5d0)
      ! SD IS THE S/D RATIO OF THE GAP BETWEEN THE TWO CYLINDERS
      parameter(lx=(26*dia)+(6*dia)+(5*sd*dia),ly=20*dia,
     &  ll=8,sav_para1=10000)

      parameter(restart_para=0) ! 0 starts frm node.dat 1 starts frm node1.dat
      parameter(anb_para = 8, anb_switch = 0,period = 1395)
      parameter(anbsave_para = 20 , clsave_para = 10)
        
    
c.....variables
c
      real*8  density
c
c.....relaxation parameter
c
      real*8  omega
c
c.....accelleration
c
      real*8  accel
c.....maximum number of iterations
c
      integer  t_max
c
c.....iteration counter
c
      integer time
c
c.....error flag
c
      logical  error
c
c.....obstacle array
c
      logical  obst(lx,ly)
c
c.....stores velocity at outlet at t-1 time step
      real*8  u_prev(ly), v_prev(ly)!, p(100)
      real*8  U0,Re,nu !freestream velocity
      parameter (U0=0.05d0)
c
c.....fluid densities
c     a 9-speed lattice is used here, other geometries are possible
c
c     the densities are numbered as follows:
c
c              6   2   5
c                \ | /
c              3 - 0 - 1
c                / | \
c              7   4   8
c
c    the lattice nodes are numbered as follows:
c
c
c     ^
c     |
c     y
c
c        :    :    :
c
c   3    *    *    *  ..
c
c   2    *    *    *  ..
c
c   1    *    *    *  ..
c                         x ->
c        1    2    3
c
c
      real*8  node(0:8,lx,ly),nodet(0:8,lx,ly)
c
c.....help array for temporarely storage of fluid densities
c
      real*8  n_hlp(0:8,lx,ly)!, e_hlp(0:ll,lx,ly)
c
c.....average velocity, computed by subroutine 'write_velocity'
c
      !real*8  vel
      real*8  cl(6), cd(6)
      real*8   p_dev(lx,ly),p_rms(lx,ly),p_avg(lx,ly)
      real*8  u_xdev(lx,ly),u_xrms(lx,ly),u_xavg(lx,ly)
      real*8  u_ydev(lx,ly),u_yavg(lx,ly),u_yrms(lx,ly)
      real*8  u_xyavg(lx,ly),u_xpavg(lx,ly),u_ypavg(lx,ly)
      real*8  Nu_t1, Nu_b1, Nu_l1, Nu_r1,Average_Nu1
      real*8  Nu_t2, Nu_b2, Nu_l2, Nu_r2, Average_Nu2
      real*8  Nu_t3, Nu_b3, Nu_l3, Nu_r3,Average_Nu3
      real*8  Nu_t4, Nu_b4, Nu_l4, Nu_r4,Average_Nu4
      real*8  Nu_t5, Nu_b5, Nu_l5, Nu_r5,Average_Nu5
      real*8  Nu_t6, Nu_b6, Nu_l6, Nu_r6,Average_Nu6
c.........thermal values
      real*8  u(lx,ly),v(lx,ly),temp(lx,ly),gbeta,pr,Ri
      integer xl,xu,x11,xuu,yuu,yll,yu
      parameter (xl=7*dia+1,xu=xl+dia)


c.....startup information message
c
      write (6,*)
      write (6,*) 'bundle 3.0 (30-May-2005)'
      write (6,*)
      write (6,*) '****************************************************'
      write (6,*) '***              anb starting ...                ***'
      write (6,*) '****************************************************'
      write (6,*) '*** Precompiled for lattice size lx = ',lx
      write (6,*) '***                              ly = ',ly
      write (6,*) '****************************************************'
      write (6,*) '***'
	  write (6,*) 'outflow BC called from the relaxation subroutine'
	  write (6,*)
c
c======================================================================c     begin initialisation
c======================================================================c
      error = .false.
	  iter = 0
	  write(*,*) 'starting with iter =', iter
c
      call read_parametrs(error,t_max,density,omega)
c
c.....if an I/O error occurs while reading the parameter file,
c     the "error"-flag is set "true" and the program stops.
c
      if (error) goto 990
c
      call read_obstacles(obst,lx,ly,xu,xl,yl,yu,dia,n_cyl,sd)
c
      if (error) goto 990

	  if (restart.eq.0) then
        call init_density(lx,ly,1.d0,density,node)
	  t0 = 0

        do y = 1, ly
                u_prev(y) = 0.d0
                v_prev(y) = 0.d0
        enddo

        do y = 1, ly
        do x = 1, lx
        u_xrms(x,y) = 0.d0
        u_xavg(x,y) = 0.d0
        u_xdev(x,y) = 0.d0
        u_yrms(x,y) = 0.d0
        u_yavg(x,y) = 0.d0
        u_ydev(x,y) = 0.d0
        p_rms(x,y) = 0.d0
        p_avg(x,y) = 0.d0
        p_dev(x,y) = 0.d0
        u_xyavg(x,y) = 0.d0
        u_xpavg(x,y) = 0.d0
        u_ypavg(x,y) = 0.d0
        temp(x,y)=0.d0
        do t=0,8
            nodet(t,x,y)=0.d0
            enddo
        enddo
        enddo

      else
	  call read_node(lx,ly,node,time
     &            ,u_xavg,u_xrms,u_xdev
     &            ,u_yavg,u_yrms,u_ydev
     &      ,p_avg,p_rms,p_dev,restart_para
     &      ,u_xyavg,u_xpavg,u_ypavg,u_prev,v_prev)

	   t0=time
        do y = 1, ly
            do x = 1, lx
                 temp(x,y)=0.d0
            do t=0,8
                nodet(t,x,y)=0.d0
                enddo
            enddo
            enddo
        endif
c
c     write(*,*) 'Enter the value of Reynolds number'
c     read(*,*) Re
      Re=100.d0
       Ri= 0.d0
        pr=0.71
      nu =(U0*dia)/Re
      omega = 2.d0/(6.d0*nu+1.d0)
c
        write(*,*) 'Re (based on obst thickness) ='
     &		   ,U0*dia*6.d0*omega/(2.d0-omega)
        write(*,*) 'omega =',omega
        write(*,*) 'omegat =',2.d0/(6.d0*nu/1.0+1.d0)
        write(*,*) 'alpha=',nu/1.0
        write(*,*) 'nu =',nu
c

c======================================================================c     end initialisation
c======================================================================c======================================================================c     begin iterations
c======================================================================c
c.....main loop

    	if(t0.eq.0) then

		open(52,file='cl02.dat')
		open(53,file='cd02.dat')
		!open(55,file='cdstr02.dat')

	  else

                open(52,file='cl02.dat',access='append')
                open(53,file='cd02.dat',access='append')
                !open(55,file='cdstr02.dat',access='append')


	     endif

         write(52,*)'VARIABLES = Time , Cl1, Cl2,Cl3,Cl4,Cl5,Cl6'
	     write(53,*)'VARIABLES = Time , Cd1, Cd2,Cd3,Cd4,Cd5,Cd6'
        ! write(55,*)'VARIABLES = Time , cd_stress1'

      open(84,file='Nusselt.dat')
       write(84,*) 'VARIABLES = Time, Nu_t1, Nu_b1, Nu_l1, Nu_r1,

     & Average_Nu1, Nu_t2, Nu_b2, Nu_l2, Nu_r2, Average_Nu2
     &  Average_Nu3, Nu_t3, Nu_b3, Nu_l3, Nu_r3, Average_Nu3,
     & Average_Nu4, Nu_t4, Nu_b4, Nu_l4, Nu_r4, Average_Nu4
     & Average_Nu5, Nu_t5, Nu_b5, Nu_l5, Nu_r5, Average_Nu5
     & Average_Nu6, Nu_t6, Nu_b6, Nu_l6, Nu_r6, Average_Nu6'

      do 100 t = 1, t_max
	     time = t0 + t
c	write(*,*) time
          	write(*,*) 'at time step =',time
             !	write(*,*) '********************************'
            !if(t.eq.101)  goto 990

c
c.......the integral fluid density is constantly checked
c
        if (mod(time,100) .eq. 0) then
          call check_density(lx,ly,node,time)
        end if
c
        call propagate(lx,ly,node,n_hlp)

        call redistribute(lx,ly,time,obst,n_hlp,accel,density,U0)
c
c.......bounc back from obstacles: this is the no-slip boundary-
c       condition.
c
        call bounceback(lx,ly,obst,node,n_hlp)

c.......density relaxation: a single time relaxation with relaxation
c       parameter omega is applied here.
	     call relaxation(density,omega,lx,ly,node,n_hlp,u_prev
     & 			 ,v_prev,obst,time)

	     if (mod(time,save_para).eq.0.or.mod(time,save_para).
     1  eq.sav_para1) then
 	    call write_node(lx,ly,node,time
     &            ,u_xavg,u_xrms,u_xdev
     &            ,u_yavg,u_yrms,u_ydev
     &      ,p_avg,p_rms,p_dev,save_para,sav_para1
     &      ,u_xyavg,u_xpavg,u_ypavg,u_prev,v_prev)

	     endif

                if(anb_switch.eq.0) then

        if ((mod(time,clsave_para) .eq. 0)) then

	     call write_velocity(lx,ly,time,t0,nu,obst,node,density,
     &           xl,yl,dia,sd,cl,cd,U0)	   ! p is delete

        write(52,*) time , cl(1), cl(2),cl(3), cl(4),cl(5), cl(6)
        write(53,*) time , cd(1), cd(2),cd(3), cd(4),cd(5), cd(6)
       ! write(55,23) time , cd_stress(1)
!21     format(' ', I6, 9F14.5, 2x)
!22     format(' ', I6, 9F14.5, 2x)
!23   !  format(' ', I6, 9F14.5, 2x)
        endif


c        if (mod(time,anbsave_para).eq.6 .or. mod(time,save_para).eq.0
c     &.or.mod(time,save_para).eq.sav_para1) then


                call write_results(lx,ly,obst,node,density,time
     &            ,u_xavg,u_xrms,u_xdev
     &            ,u_yavg,u_yrms,u_ydev
     &	    ,p_avg,p_rms,p_dev,save_para,sav_para1
     &	    ,u_xyavg,u_xpavg,u_ypavg,clsave_para,anbsave_para,temp)

c	endif

		    elseif (anb_switch.eq.1) then

                call write_anb(lx,ly,obst,node,density,time
     &            ,anb_para,period,t0)

		    endif
               !if ((t.ge.20000).and.(mod(time,10) .eq. 0)) then
		    	!write(*,*) '---------------------'
                !write(*,*) 'called temperature subroutine'
        call tf(lx,ly,node,nodet,obst,temp,nu,xl,yl,sd,dia,t,time)
        !endif
c.....end of the main loop
c	write(*,*) time
  100 continue
c		close(50)
            close(52)
            close(53)
            close(55)
            close(84)
c		close(54)
	     write(*,*) time

      goto 999
c
  990 write (6,*) '!!! error: program stopped during iteration =', time
      write (6,*) '!!!'
c
  999 continue



      write (6,*) '********************    end     ********************'
c
      stop
      end
c
c
****************************************************
      subroutine read_parametrs(error,t_max,density,omega)
c
      
      real*8  density,omega
      integer  t_max
      logical  error
c
c.....open parameter file
      open(10,file='multi.par')
c
c.......line 1: number of iterations
        read(10,*,err=900) t_max
c
c.......line 2: fluid density per link
        read(10,*,err=900) density
c
c.......line 3: relaxation parameter
        read(10,*,err=900) omega
c
c.....close parameter file
      close(10)
c
      write (6,*) '*** Paramters read from file multi.par.'
      write (6,*) '***'
c
      goto 999
c
c.....error message: file read error
c
  900 write (6,*) '!!! Error reading file multi.par'
      write (6,*) '!!!'
c
      goto 990
c
  990 error = .true.
c
  999 continue
c
      return
      end
c
c
****************************************************
      subroutine read_obstacles(obst,lx,ly,xu,xl,yl,yu,dia,n_cyl,sd)
c
      
      integer  lx,ly
      real*8   sd
      logical  obst(lx,ly)
      integer x1,y1,i,xl,yl,dia,xu,n_cyl,yu
      integer xll,xuu,yll,yuu,p,q
c
c.....no obstacles in obstacle array
        do 10 y1 = 1, ly
          do 10 x1 = 1, lx
   10       obst(x1,y1) = .false.
c
c.....now start placing the obstacles
      do y1 = 1, ly
	  do x1 = 1, lx
      do i = 1, n_cyl
	  yl = (9.5*dia) + 1
	  yu = yl + dia 

c	write(*,*) yl

	  if (x1.ge.(xl+((i-1)*dia*(1.+sd))).and.x1.
     &   le.(xu+((i-1)*dia*(1.+sd))).and.y1
     &   .ge.yl.and.y1.le.yu) then

      obst(x1,y1)=.true.
         endif
	     enddo
	     enddo
      enddo
      

	  open(22,file='obst.dat')
      write(22,*) 'VARIABLES = X, Y, OBST'
        write(22,*) 'ZONE I=', lx, ', J=', ly, ', F=POINT'
    	do y1 = 1, ly
	  do x1 = 1, lx
	  if(obst(x1,y1)) then
	  write(22,*) x1,y1,1
         else
		write(22,*) x1,y1,0
         end if
	  enddo
	  enddo
	  close(22)

      return
      end
c
c
****************************************************
      subroutine init_density(lx,ly,density,eps,node)
c
      
c
      integer  lx,ly
c
      real*8  density,eps,node(0:8,lx,ly)
c
c.....local variables
c
      integer  x,y
      real*8  t_0,t_1,t_2
c
c.....compute weighting factors (depending on lattice geometry)
c
      t_0 = density *  4.d0 / 9.d0
      t_1 = density /  9.d0
      t_2 = density / 36.d0
c
c.....loop over computational domain
c
      do 10 x = 1, lx
        do 10 y = 1, ly
c
c.........zero velocity density
c
          node(0,x,y) = t_0 * eps
c
c.........equilibrium densities for axis speeds
c
          node(1,x,y) = t_1 * eps
          node(2,x,y) = t_1 * eps
          node(3,x,y) = t_1 * eps
          node(4,x,y) = t_1 * eps
c
c.........equilibrium densities for diagonal speeds
c
          node(5,x,y) = t_2 * eps
          node(6,x,y) = t_2 * eps
          node(7,x,y) = t_2 * eps
          node(8,x,y) = t_2 * eps
c
   10 continue
c
      return
      end
cs
c
****************************************************
      subroutine check_density(lx,ly,node,time)
c
      
c
      integer  lx,ly,time
      real*8  node(0:8,lx,ly)
      integer  x,y,n
      real*8 n_sum
c
      n_sum = 0.d0
        do 10 y = 1, ly
          do 10 x = 1, lx
            do 10 n = 0, 8
   10         n_sum = n_sum + node(n,x,y)
c
      write(6,*) '*** Iteration number = ', time
      write(6,*) '*** Integral density = ', n_sum
      write(6,*) '***'
c
      return
      end
c
c
****************************************************

****************************************************
      subroutine write_node(lx,ly,node,time
     &            ,u_xavg,u_xrms,u_xdev
     &            ,u_yavg,u_yrms,u_ydev
     &      ,p_avg,p_rms,p_dev,save_para,sav_para1
     &      ,u_xyavg,u_xpavg,u_ypavg,u_prev,v_prev)

c
      
c
      integer  lx,ly,time,save_para,sav_para1
      real*8  node(0:8,lx,ly),u_prev(ly),v_prev(ly)
      integer  x,y
      real*8   p_dev(lx,ly),p_rms(lx,ly),p_avg(lx,ly)
      real*8  u_xdev(lx,ly),u_xrms(lx,ly),u_xavg(lx,ly)
      real*8  u_ydev(lx,ly),u_yavg(lx,ly),u_yrms(lx,ly)
      real*8  u_xyavg(lx,ly),u_xpavg(lx,ly),u_ypavg(lx,ly)


	  if(mod(time,save_para).eq.0) then

	  open(68,file='node.dat')
	  write(68,*) time
	  open(13,file='uprev.dat')

        do 11 y = 1, ly
          do 11 x = 1, lx

	  write(68,*) x,y,node(0,x,y),node(1,x,y),node(2,x,y),node(3,x,y)
     &,node(4,x,y),node(5,x,y),node(6,x,y),node(7,x,y),node(8,x,y)


   11   continue

        do y = 1, ly
        write(13,*) lx,y,u_prev(y),v_prev(y)
        enddo

	  close(68)
	  close(13)

	  endif

	  if(mod(time,save_para).eq.sav_para1) then


	  open(98,file='node1.dat')
        write(98,*) time
        open(43,file='uprev1.dat')

        do 13 y = 1, ly
          do 13 x = 1, lx

        write(98,*) x,y,node(0,x,y),node(1,x,y),node(2,x,y),node(3,x,y)
     &,node(4,x,y),node(5,x,y),node(6,x,y),node(7,x,y),node(8,x,y)


   13   continue

        do y = 1, ly
        write(43,*) lx,y,u_prev(y),v_prev(y)
        enddo

        close(98)
        close(43)

	  endif

      return
      end
c
c
****************************************************

****************************************************
      subroutine read_node(lx,ly,node,time
     &            ,u_xavg,u_xrms,u_xdev
     &            ,u_yavg,u_yrms,u_ydev
     &      ,p_avg,p_rms,p_dev,restart_para
     &      ,u_xyavg,u_xpavg,u_ypavg,u_prev,v_prev)


c
      
c
      integer  lx,ly,time,restart_para
      real*8  node(0:8,lx,ly),u_prev(ly),v_prev(ly)
      integer  x,y,x1
      real*8   p_dev(lx,ly),p_rms(lx,ly),p_avg(lx,ly)
      real*8  u_xdev(lx,ly),u_xrms(lx,ly),u_xavg(lx,ly)
      real*8  u_ydev(lx,ly),u_yavg(lx,ly),u_yrms(lx,ly)
      real*8  u_xyavg(lx,ly),u_xpavg(lx,ly),u_ypavg(lx,ly)
      character read_line

	  if(restart_para.eq.0) then
        open(69,file='node.dat')
	  read(69,*) time
	  open(12,file='rms.dat')
	  read(12,*) read_line
	  read(12,*) read_line
	  open(14,file='uprev.dat')

        do 12 y = 1, ly
          do 12 x = 1, lx

        read(69,*) x1,x1,node(0,x,y),node(1,x,y),node(2,x,y),node(3,x,y)
     &,node(4,x,y),node(5,x,y),node(6,x,y),node(7,x,y),node(8,x,y)

        read(12,*) x1,x1,u_xavg(x,y),u_xrms(x,y),u_xdev(x,y),u_yavg(x,y)
     &,u_yrms(x,y),u_ydev(x,y),p_avg(x,y),p_rms(x,y),p_dev(x,y),
     &u_xyavg(x,y),u_xpavg(x,y),u_ypavg(x,y)


   12   continue

        do y = 1, ly
        read(14,*) x1,x1,u_prev(y),v_prev(y)
        enddo


        close(69)
	  close(12)
	  close(14)

	  endif

        if(restart_para.eq.1) then
        open(69,file='node1.dat')
        read(69,*) time
        open(12,file='rms1.dat')
        read(12,*) read_line
        read(12,*) read_line
        open(14,file='uprev1.dat')

        do 13 y = 1, ly
          do 13 x = 1, lx

        read(69,*) x1,x1,node(0,x,y),node(1,x,y),node(2,x,y),node(3,x,y)
     &,node(4,x,y),node(5,x,y),node(6,x,y),node(7,x,y),node(8,x,y)

        read(12,*) x1,x1,u_xavg(x,y),u_xrms(x,y),u_xdev(x,y),u_yavg(x,y)
     &,u_yrms(x,y),u_ydev(x,y),p_avg(x,y),p_rms(x,y),p_dev(x,y),
     &u_xyavg(x,y),u_xpavg(x,y),u_ypavg(x,y)


   13   continue

        do y = 1, ly
        read(14,*) x1,x1,u_prev(y),v_prev(y)
        enddo


        close(69)
        close(12)
        close(14)

        endif

      return
      end
c
c
****************************************************


****************************************************

      subroutine redistribute(lx,ly,time,obst,node,accel,density,U0)
c
      
      integer  lx,ly
      logical  obst(lx,ly)
      real*8   node(0:8,lx,ly),accel,density,U0
	  real*8	 noise
      integer  x,y,i,time
      real*8  t_0,t_1,t_2,c_squ,u_squ,u_n(8),n_equ(0:8),u_x
      real*8  d_loc,u_y
c
	  t_0 = 4.d0 / 9.d0
      t_1 = 1.d0 /  9.d0
      t_2 = 1.d0 / 36.d0
      c_squ = 1.d0 / 3.d0
c
      x = 1
	  do y = 1, ly
	   if ( .not. obst(x,y)) then
c
            d_loc = 0.d0
            do 20 i = 0, 8
              d_loc = d_loc + node(i,x,y)
   20       continue
c
c		  call random(noise)
	      u_x = U0 !* ( 1.d0 - (y-ly/2.d0)**2.d0 / (ly/2.d0)**2.d0)
	      u_y = 0.d0

            u_squ = u_x * u_x + u_y * u_y
c
            u_n(1) =   u_x
            u_n(2) =         u_y
            u_n(3) = - u_x
            u_n(4) =       - u_y
            u_n(5) =   u_x + u_y
            u_n(6) = - u_x + u_y
            u_n(7) = - u_x - u_y
            u_n(8) =   u_x - u_y
c
            n_equ(0) = t_0 * d_loc * (1.d0 - u_squ / (2.d0 * c_squ))
c
            do i = 1, 4
              n_equ(i) = t_1 * d_loc * (1.d0 + u_n(i) / c_squ
     &               + u_n(i) ** 2.d0 / (2.d0 * c_squ ** 2.d0)
     &               - u_squ / (2.d0 * c_squ))
            enddo
c
            do i = 5, 8
              n_equ(i) = t_2 * d_loc * (1.d0 + u_n(i) / c_squ
     &               + u_n(i) ** 2.d0 / (2.d0 * c_squ ** 2.d0)
     &               - u_squ / (2.d0 * c_squ))
            enddo
c
            do 30 i = 0, 8
              node(i,x,y) = n_equ(i)
   30       continue
         endif
      enddo

      return
      end
c
c
****************************************************
      subroutine bounceback(lx,ly,obst,node,n_hlp)
c
      
c
      integer  lx,ly
      logical  obst(lx,ly)
      real*8   node(0:8,lx,ly),n_hlp(0:8,lx,ly)
      integer  x,y
c
c.....loop over all nodes
c
      do 10 x = 1, lx
        do 10 y = 1, ly
c
c.........consider only obstacle nodes

          if (obst(x,y)) then
            node(1,x,y) = n_hlp(3,x,y)
            node(2,x,y) = n_hlp(4,x,y)
            node(3,x,y) = n_hlp(1,x,y)
	    node(4,x,y) = n_hlp(2,x,y)
            node(5,x,y) = n_hlp(7,x,y)
            node(6,x,y) = n_hlp(8,x,y)
            node(7,x,y) = n_hlp(5,x,y)
            node(8,x,y) = n_hlp(6,x,y)
          end if
c
   10 continue
c

c
      return
      end
c
c
******************************************************
      subroutine propagate(lx,ly,node,n_hlp)
c
      
      integer  lx,ly
      real*8   node(0:8,lx,ly),n_hlp(0:8,lx,ly)
      integer  x,y,x_e,x_w,y_n,y_s,i
c
      do 10 x = 1, lx
        do 10 y = 1, ly
c
c.........compute upper and right next neighbour nodes with regard
c         to periodic boundaries
          y_n = mod(y,ly) + 1
          x_e = mod(x,lx) + 1
c
c.........compute lower and left next neighbour nodes with regard to
c         periodic boundaries
          y_s = ly - mod(ly + 1 - y, ly)
          x_w = lx - mod(lx + 1 - x, lx)
c
c.........density propagation
c
c.........zero: just copy
          n_hlp(0,x  ,y  ) = node(0,x,y)
c
c.........east
          n_hlp(1,x_e,y  ) = node(1,x,y)
c
c.........north
          n_hlp(2,x  ,y_n) = node(2,x,y)
c
c.........west
          n_hlp(3,x_w,y  ) = node(3,x,y)
c
c.........south
          n_hlp(4,x  ,y_s) = node(4,x,y)
c
c.........north-east
          n_hlp(5,x_e,y_n) = node(5,x,y)
c
c.........north-west
          n_hlp(6,x_w,y_n) = node(6,x,y)
c
c.........south-west
          n_hlp(7,x_w,y_s) = node(7,x,y)
c
c.........south-east
          n_hlp(8,x_e,y_s) = node(8,x,y)
   10 continue

      return
      end
c
c
**************************************************************
c     One-step density relaxation process
**************************************************************
      subroutine relaxation(density,omega,lx,ly,node,n_hlp,
     &				 	  u_prev,v_prev,obst,time)
c
      
      integer  lx,ly,time
      logical  obst(lx,ly)
      real*8   density,omega,node(0:8,lx,ly),n_hlp(0:8,lx,ly)
 	  real*8   u_curr(ly),u_bdy1(ly),u_prev(ly)	! u_curr: at boundary
							! u_bdy1: at boundary - 1 (in x)							! u_prev: at boundary - 1 (in time)
	  real*8   v_curr(ly),v_bdy1(ly),v_prev(ly)
      integer  x,y,i
      real*8  c_squ,t_0,t_1,t_2,u_x,u_y,u_n(8),n_equ(0:8)
      real*8  u_squ,d_loc
	  real*8    noise
c
      t_0 = 4.d0 / 9.d0
      t_1 = 1.d0 /  9.d0
      t_2 = 1.d0 / 36.d0
      c_squ = 1.d0 / 3.d0
c
      do y = 1, ly
        do x = 1, lx
c.........only free nodes are considered here
          if (.not. obst(x,y)) then
c
            d_loc = 0.d0
            do i = 0, 8
              d_loc = d_loc + n_hlp(i,x,y)
		  enddo
c
c...........x-, and y- velocity components
            u_x = (n_hlp(1,x,y) + n_hlp(5,x,y) + n_hlp(8,x,y)
     &           -(n_hlp(3,x,y) + n_hlp(6,x,y) + n_hlp(7,x,y))) / d_loc
c
            u_y = (n_hlp(2,x,y) + n_hlp(5,x,y) + n_hlp(6,x,y)
     &           -(n_hlp(4,x,y) + n_hlp(7,x,y) + n_hlp(8,x,y))) / d_loc

c...........x-, and y- velocity components
            u_x = (n_hlp(1,x,y) + n_hlp(5,x,y) + n_hlp(8,x,y)
     &           -(n_hlp(3,x,y) + n_hlp(6,x,y) + n_hlp(7,x,y))) / d_loc
c
            u_y = (n_hlp(2,x,y) + n_hlp(5,x,y) + n_hlp(6,x,y)
     &           -(n_hlp(4,x,y) + n_hlp(7,x,y) + n_hlp(8,x,y))) / d_loc

           if (y.eq.1.and.x.ge.1.and.x.le.lx) then
c       u_x= 0 !(n_hlp(1,x,y+1) + n_hlp(5,x,y+1) + n_hlp(8,x,y+1)
c     &     -(n_hlp(3,x,y+1) + n_hlp(6,x,y+1) + n_hlp(7,x,y+1))) / d_loc
        u_y=0.d0
        endif

        if (y.eq.ly.and.x.ge.1.and.x.le.lx) then
c       u_x=0 !(n_hlp(1,x,y-1) + n_hlp(5,x,y-1) + n_hlp(8,x,y-1)
c     &      -(n_hlp(3,x,y-1) + n_hlp(6,x,y-1) + n_hlp(7,x,y-1))) / d_loc
        u_y=0.d0
        endif

c...........square velocity
            u_squ = u_x * u_x + u_y * u_y
c
c...........n- velocity components (n = lattice node connection vectors)
c...........this is only necessary for clearence, and only 3 speeds would
c...........be necessary
c
            u_n(1) =   u_x
            u_n(2) =         u_y
            u_n(3) = - u_x
            u_n(4) =       - u_y
            u_n(5) =   u_x + u_y
            u_n(6) = - u_x + u_y
            u_n(7) = - u_x - u_y
            u_n(8) =   u_x - u_y
c
c...........equilibrium densities
c
c...........zero velocity density
            n_equ(0) = t_0 * d_loc * (1.d0 - u_squ / (2.d0 * c_squ))
c
c...........axis speeds (factor: t_1)
		  do i = 1, 4
			n_equ(i) = t_1 * d_loc * (1.d0 + u_n(i) / c_squ
     &               + u_n(i) ** 2.d0 / (2.d0 * c_squ ** 2.d0)
     &               - u_squ / (2.d0 * c_squ))
		  enddo
c
c...........diagonal speeds (factor: t_2)
		  do i = 5, 8
			n_equ(i) = t_2 * d_loc * (1.d0 + u_n(i) / c_squ
     &               + u_n(i) ** 2.d0 / (2.d0 * c_squ ** 2.d0)
     &               - u_squ / (2.d0 * c_squ))
		  enddo
c
c...........relaxation step
            do i = 0, 8
              node(i,x,y) = n_hlp(i,x,y)
     &                      + omega * (n_equ(i) - n_hlp(i,x,y))
            enddo
c
          end if

		if (x.eq.lx-1) then
		  u_bdy1(y) = u_x
		  v_bdy1(y) = u_y
		endif
	  enddo ! x-loop
c
	  u_curr(y) = u_x
	  v_curr(y) = u_y
	  enddo	! y-loop
c
        call convective_BC(lx,ly,obst,node,u_curr,u_bdy1,u_prev
     &					,v_curr,v_bdy1,v_prev,omega)
c
      return
      end
c
c
****************************************************
	  subroutine convective_BC(lx,ly,obst,n_hlp,u_curr,u_bdy1,u_prev
     &									 ,v_curr,v_bdy1,v_prev,omega)
c
      
      integer  lx,ly
      real*8   n_hlp(0:8,lx,ly),u_curr(ly)
      real*8	 v_curr(ly),v_prev(ly),v_bdy1(ly)
      real*8    u_prev(ly),u_bdy1(ly),Uc
      integer  x,y,i,num
      logical  obst(lx,ly)
      real*8  c_squ,t_0,t_1,t_2,u_x,u_y,u_n(8),n_equ(0:8)
      real*8	u_squ,d_loc,omega
c
      t_0 = 4.d0 / 9.d0
      t_1 = 1.d0 /  9.d0
      t_2 = 1.d0 / 36.d0
      c_squ = 1.d0 / 3.d0
	  x = lx
c
c.....first compute the mean outflow velocity, Uc
            Uc = 0.d0
        num = 0
	     do y = 1, ly
	  if (.not.obst(x,y)) then
		Uc = Uc + u_curr(y)
		num = num + 1
	     endif
	     enddo
	  Uc = Uc/num !if (num.gt.0) check not needed
c
c.....compute the new velocities (based on convective BC)
	  do y = 1, ly
	  if (.not.obst(x,y)) then
		u_curr(y) = (u_prev(y) + Uc*u_bdy1(y))/(1.d0+Uc)
		u_prev(y) = u_curr(y)
		v_curr(y) = (v_prev(y) + Uc*v_bdy1(y))/(1.d0+Uc)
		v_prev(y) = v_curr(y)
	  endif
	  enddo
c
c.....now re-assign the densities at the outflow boundary
	  do y = 1, ly
	  if (.not.obst(x,y)) then
            d_loc = 0.d0
            do i = 0, 8
              d_loc = d_loc + n_hlp(i,x,y)
		  enddo
c
            u_x = u_curr(y)
		if (y.ge.1.and.y.le.ly-1) then
            u_y = v_curr(y)
		else
	      u_y = (n_hlp(2,x,y) + n_hlp(5,x,y) + n_hlp(6,x,y)
     &           -(n_hlp(4,x,y) + n_hlp(7,x,y) + n_hlp(8,x,y))) / d_loc
		endif
c
            u_squ = u_x * u_x + u_y * u_y
c
            u_n(1) =   u_x
            u_n(2) =         u_y
            u_n(3) = - u_x
            u_n(4) =       - u_y
            u_n(5) =   u_x + u_y
            u_n(6) = - u_x + u_y
            u_n(7) = - u_x - u_y
            u_n(8) =   u_x - u_y
c
            n_equ(0) = t_0 * d_loc * (1.d0 - u_squ / (2.d0 * c_squ))
c
		  do i = 1, 4
			n_equ(i) = t_1 * d_loc * (1.d0 + u_n(i) / c_squ
     &               + u_n(i) ** 2.d0 / (2.d0 * c_squ ** 2.d0)
     &               - u_squ / (2.d0 * c_squ))
		  enddo
c
		  do i = 5, 8
			n_equ(i) = t_2 * d_loc * (1.d0 + u_n(i) / c_squ
     &               + u_n(i) ** 2.d0 / (2.d0 * c_squ ** 2.d0)
     &               - u_squ / (2.d0 * c_squ))
		  enddo
c
            do i = 0, 8
              n_hlp(i,x,y) = n_hlp(i,x,y)
     &                      + omega * (n_equ(i) - n_hlp(i,x,y))
            enddo
	   endif
	  enddo
c
	  return
	  end
c
c
***************************************************************************
      subroutine write_velocity(lx,ly,time,t0,nu,obst,node,density,
     &		 xl,yl,dia,sd,cl,cd,U0)  ! p is deleted

      
      integer  lx,ly,time,t0
      logical  obst(lx,ly)
      real*8   node(0:8,lx,ly),nu
      integer  x,y,z,i
      real*8   u_x1,U0,cl(6),cd(6),d_loc,sd
      integer  dia,xl,yl,k,xll,xuu,yll,yuu
        real*8   pl,pr,pt,pb,sl,sb,st,sr,density,u_xtemp
c
	!real*8	 u_x,u_y
	!real*8	 d_loc,d_loc5,d_loc6,vel,density
c

c	real*8	 p_lower_bot(n_cyl), p_lower_top(n_cyl),
c     1           p_lower_left(n_cyl)
c        real*8   p_lower_right(n_cyl)
c	  real*8	 p_upper_bot, p_upper_top, p_upper_left, p_upper_right
c	  real*8	 drag_lowerf, drag_upperf, lift_lowerf, lift_upperf !,p(100)
c	integer       x1,x2,y1,y2,d
c
c	real*8  drag_lower(n_cyl), lift_lower(n_cyl)
c	real*8	cd(n_cyl),cl(n_cyl)
c	real*8  stress_top(n_cyl),stress_bot(n_cyl),
c     1          cd_stress(n_cyl),u_xtemp,
c     &          stress_left(n_cyl), stress_right(n_cyl),
c     1          lift_stress(n_cyl)
c	 if (x.ge.71.and.x.le.80.and.y.ge. 61.and.y.le. 70)obst(x,y)=.true.
c	 if (x.ge.71.and.x.le.80.and.y.ge.101.and.y.le.110)obst(x,y)=.true.
c	 if (x.ge.71.and.x.le.80.and.y.ge.141.and.y.le.150)obst(x,y)=.true.
c	 if (x.ge.71.and.x.le.80.and.y.ge.181.and.y.le.190)obst(x,y)=.true.


c     edited code myp
        write (*,*) '************************************************'
       xl=7*dia+1
       yl=9.5*dia+1
      do i=1,6
        
            xll=xl+ (i-1)*(sd+1)*dia
            xuu=xll+dia
            yll=yl
            yuu=yll+dia
            sl=0.d0
            sr=0.d0
            sb=0.d0
            st=0.d0
            pl=0.d0
            pr=0.d0
            pb=0.d0
            pt=0.d0

c pressure on bottom
            y=yll-1

            d_loc = 0.d0
	        do x = xll, xuu

	          do k = 0, 8
		       d_loc = d_loc + node(k,x,y)
	          enddo

          enddo
	     pb = d_loc/3.d0

         d_loc = 0.d0
	        do x = xll, xuu

	          do k = 0, 8
		       d_loc = d_loc + node(k,x,y)
	          enddo
               u_xtemp = (node(1,x,y) + node(5,x,y) + node(8,x,y)
     &               -(node(3,x,y) + node(6,x,y) + node(7,x,y))) / d_loc

       sb = sb + u_xtemp*2*nu*d_loc

          enddo




c pressure on top
          y=yuu+1
         d_loc = 0.d0
	        do x = xll, xuu

	          do k = 0, 8
		       d_loc = d_loc + node(k,x,y)
	          enddo

          enddo
	     pt = d_loc/3.d0

         d_loc = 0.d0
	        do x = xll, xuu

	          do k = 0, 8
		       d_loc = d_loc + node(k,x,y)
	          enddo
               u_xtemp = (node(1,x,y) + node(5,x,y) + node(8,x,y)
     &               -(node(3,x,y) + node(6,x,y) + node(7,x,y))) / d_loc

       st = st + u_xtemp*2*nu*d_loc

          enddo

c pressure on left side
          x=xll-1
         d_loc = 0.d0
	        do y = yll, yuu

	          do k = 0, 8
		       d_loc = d_loc + node(k,x,y)
	          enddo

          enddo
	     pl = d_loc/3.d0

         d_loc = 0.d0
	        do y = yll, yuu

	          do k = 0, 8
		       d_loc = d_loc + node(k,x,y)
	          enddo

              u_xtemp = (node(1,x,y) + node(5,x,y) + node(8,x,y)
     &               -(node(3,x,y) + node(6,x,y) + node(7,x,y))) / d_loc

       sl = sl + u_xtemp*2*nu*d_loc


          enddo

c pressure on right side
          x=xuu+1
         d_loc = 0.d0
	        do y = yll, yuu

	          do k = 0, 8
		       d_loc = d_loc + node(k,x,y)
	          enddo

          enddo
	     pr = d_loc/3.d0

         d_loc = 0.d0
	        do y = yll, yuu

	          do k = 0, 8
		       d_loc = d_loc + node(k,x,y)
	          enddo

              u_xtemp = (node(1,x,y) + node(5,x,y) + node(8,x,y)
     &               -(node(3,x,y) + node(6,x,y) + node(7,x,y))) / d_loc

       sr = sr + u_xtemp*2*nu*d_loc


          enddo

          cd(i)=((pl-pr)+(st+sb))/(0.5d0*dia*density*U0**2)
          cl(i)=((pt-pb)+(sl+sr))/(0.5d0*dia*density*U0**2)


        ! enddo
      enddo
       return
       end
c
c
****************************************************
      subroutine  write_results(lx,ly,obst,node,density,time
     &            ,u_xavg,u_xrms,u_xdev
     &            ,u_yavg,u_yrms,u_ydev
     &	    ,p_avg,p_rms,p_dev,save_para,sav_para1
     &	    ,u_xyavg,u_xpavg,u_ypavg,clsave_para,anbsave_para,temp)
c
      
      integer  lx,ly,save_para,sav_para1,anbsave_para,clsave_para
      real*8  node(0:8,lx,ly),density
      logical  obst(lx,ly)
      integer  x,y,i,obsval,iter,time
      real*8 u_x,u_y,d_loc,press,c_squ,u_xsqusum
      real*8 u_xdiffsqu,u_xdiffsqusum,u_xsum,u_xsqu
      real*8 u_xdev(lx,ly),u_xrms(lx,ly),u_xavg(lx,ly)
      real*8 u_yrms(lx,ly),u_yavg(lx,ly),u_ydev(lx,ly)
      real*8 u_ydiffsqu,u_ydiffsqusum,u_ysum,u_ysqusum,u_ysqu
      real*8 p_rms(lx,ly),p_avg(lx,ly),p_dev(lx,ly)
      real*8 p_diffsqu,p_diffsqusum,p_sum,p_squsum,p_squ
      real*8 u_xyavg(lx,ly),u_xy,u_xysum
      real*8 u_xpavg(lx,ly),u_xp,u_xpsum
      real*8 u_ypavg(lx,ly),u_yp,u_ypsum
      real*8 temp(lx,ly)
c	real*8	u(lx,ly),v(lx,ly) !,omega_z(lx,ly)
	     character*3  str
	     character*20 filename

        c_squ = 1.d0 / 3.d0



	  if (mod(time,anbsave_para).eq.0) then
	     open(11,file='anb903.dat')
	         write(11,*) 'VARIABLES = X, Y, VX, VY, PRESS, OBST'
      		write(11,*) 'ZONE I=', lx, ', J=', ly, ', F=POINT'
        open(85,file='Temperature_field.dat')
      		write(85,*) 'VARIABLES = X, Y, TEMP'
      		write(85,*) 'ZONE I=', lx, ', J=', ly, ', F=POINT'
	  endif

	  if (mod(time,save_para).eq.0) then

	  open(12,file='rms.dat')
                 write(12,*) 'VARIABLES = X, Y, VXavg, VXrms, VXdev,
     & VYavg, VYrms, VYdev, Pavg, Prms, Pdev,VXYavg, VXPavg, VYPavg'
                write(12,*) 'ZONE I=', lx, ', J=', ly, ', F=POINT'
	  endif

	  if (mod(time,save_para).eq.sav_para1) then

        open(21,file='rms1.dat')
                 write(21,*) 'VARIABLES = X, Y, VXavg, VXrms, VXdev,
     & VYavg, VYrms, VYdev, Pavg, Prms, Pdev,VXYavg, VXPavg, VYPavg'
                write(21,*) 'ZONE I=', lx, ', J=', ly, ', F=POINT'
	  endif

c.....loop over all nodes
      do 10 y = 1, ly
        do 10 x = 1, lx
c
            d_loc = 0.d0
c		  e_loc = 0.d0
            do 20 i = 0, 8
              d_loc = d_loc + node(i,x,y)
c		    e_loc = e_loc + ener(i,x,y)
   20       continue
c
          if (obst(x,y)) then
            obsval = 1
            u_x = 0.d0
            u_y = 0.d0
c
		else
	      obsval = 0
            u_x = (node(1,x,y) + node(5,x,y) + node(8,x,y)
     &           -(node(3,x,y) + node(6,x,y) + node(7,x,y))) / d_loc
            u_y = (node(2,x,y) + node(5,x,y) + node(6,x,y)
     &           -(node(4,x,y) + node(7,x,y) + node(8,x,y))) / d_loc
          end if

	  press = d_loc * c_squ
*******************************************test code*************
c		if (x==(268).and.y==(179)) then
c		ux_temp=u_x
c		uy_temp=u_y
c		endif
*******************************************test ends*************

******************************************* rms,avg,deviation calculation********************



        u_xsqu = u_x * u_x
        u_xsqusum = (u_xrms(x,y)*u_xrms(x,y)*(time-1)) + u_xsqu
        u_xsum = (u_xavg(x,y)*(time-1)) + u_x
	  u_xdiffsqu = (u_x-u_xavg(x,y))*(u_x-u_xavg(x,y))
	  u_xdiffsqusum = u_xdev(x,y)*u_xdev(x,y)*(time-1) + u_xdiffsqu
	  u_xdev(x,y) = sqrt(u_xdiffsqusum/time)
        u_xrms(x,y) = sqrt(u_xsqusum/time)
        u_xavg(x,y) = u_xsum/time

        u_ysqu = u_y * u_y
        u_ysqusum = (u_yrms(x,y)*u_yrms(x,y)*(time-1)) + u_ysqu
        u_ysum = (u_yavg(x,y)*(time-1)) + u_y
        u_ydiffsqu = (u_y-u_yavg(x,y))*(u_y-u_yavg(x,y))
        u_ydiffsqusum = u_ydev(x,y)*u_ydev(x,y)*(time-1) + u_ydiffsqu
	  u_ydev(x,y) = sqrt(u_ydiffsqusum/time)
        u_yrms(x,y) = sqrt(u_ysqusum/time)
        u_yavg(x,y) = u_ysum/time

    	p_squ = press * press
        p_squsum = (p_rms(x,y)*p_rms(x,y)*(time-1)) + p_squ
        p_sum = (p_avg(x,y)*(time-1)) + press
        p_diffsqu = (press-p_avg(x,y))*(press-p_avg(x,y))
        p_diffsqusum = p_dev(x,y)*p_dev(x,y)*(time-1) + p_diffsqu
	   p_dev(x,y) = sqrt(p_diffsqusum/time)
        p_rms(x,y) = sqrt(p_squsum/time)
        p_avg(x,y) = p_sum/time

	  u_xy = (sqrt(u_xdiffsqu)*sqrt(u_ydiffsqu))
	  u_xysum = u_xyavg(x,y)*(time-1) + u_xy
	  u_xyavg(x,y) = u_xysum/time

	  u_xp = (sqrt(u_xdiffsqu)*sqrt(p_diffsqu))
	  u_xpsum = u_xpavg(x,y)*(time-1) + u_xp
	  u_xpavg(x,y) = u_xpsum/time

	  u_yp = (sqrt(u_ydiffsqu)*sqrt(p_diffsqu))
	  u_ypsum = u_ypavg(x,y)*(time-1) + u_yp
	  u_ypavg(x,y) = u_ypsum/time

********************************************** finish***************************************



	  if (mod(time,anbsave_para).eq.0) then
		write(11,*) x,y,u_x,u_y,press,obsval
		write(85,*) x,y,temp(x,y)
	  endif

	  if (mod(time,save_para).eq.0) then

	  write(12,*) x,y,u_xavg(x,y),u_xrms(x,y),u_xdev(x,y),u_yavg(x,y),
     &u_yrms(x,y),u_ydev(x,y),p_avg(x,y),p_rms(x,y),p_dev(x,y),
     &u_xyavg(x,y),u_xpavg(x,y),u_ypavg(x,y)
	  endif

	  if (mod(time,save_para).eq.sav_para1) then

        write(21,*) x,y,u_xavg(x,y),u_xrms(x,y),u_xdev(x,y),u_yavg(x,y),
     &u_yrms(x,y),u_ydev(x,y),p_avg(x,y),p_rms(x,y),p_dev(x,y),
     &u_xyavg(x,y),u_xpavg(x,y),u_ypavg(x,y)

	  endif

   10 continue

c
c.....close files

	  if (mod(time,anbsave_para).eq.0) then
           close(11)
           close(85)
	     endif

	     if (mod(time,save_para).eq.0) then

	      close(12)
	     endif

        if (mod(time,save_para).eq.sav_para1) then

           close(21)
        endif


      return
      end

**************************************************************************
	     subroutine write_anb(lx,ly,obst,node,density,time
     &            ,anb_para,period,t0)

      
      integer  lx,ly,anb_para,period
      real*8  node(0:8,lx,ly),density
      logical  obst(lx,ly)
      integer  x,y,i,j,obsval,iter,time,t0,t1,quotient
      real*8 u_x,u_y,d_loc,press,c_squ

      c_squ = 1.d0 / 3.d0
      quotient = period/anb_para

	  t1 = t0+1
	     if(time.eq.t1) then
           open(90,file='anb0.dat')
           open(91,file='anb1.dat')
           open(92,file='anb2.dat')
           open(93,file='anb3.dat')
           open(94,file='anb4.dat')
           open(95,file='anb5.dat')
           open(96,file='anb6.dat')
           open(97,file='anb7.dat')
           open(98,file='anb8.dat')

		    do i=0,anb_para
                write((90+i),*) 'VARIABLES = X, Y, VX, VY, PRESS, OBST'
                write((90+i),*) 'ZONE I=', lx, ', J=', ly, ', F=POINT'
		    enddo

	     endif

        do j= 0,anb_para
                if(time.eq.(t0+j*quotient+1)) then

c.....loop over all nodes
      do  y = 1, ly
        do  x = 1, lx
c
            d_loc = 0.d0
            do 20 i = 0, 8
              d_loc = d_loc + node(i,x,y)
   20       continue
c
c
          if (obst(x,y)) then
            obsval = 1
            u_x = 0.d0
            u_y = 0.d0
c
                else
              obsval = 0
            u_x = (node(1,x,y) + node(5,x,y) + node(8,x,y)
     &           -(node(3,x,y) + node(6,x,y) + node(7,x,y))) / d_loc
            u_y = (node(2,x,y) + node(5,x,y) + node(6,x,y)
     &           -(node(4,x,y) + node(7,x,y) + node(8,x,y))) / d_loc
          end if

        press = d_loc * c_squ

                write((90+j),*) x,y,u_x,u_y,press,obsval
        enddo
        enddo

c
c.....close files

           close((90+j))
                endif
        enddo

		if (time.ge.(t0+period)) then
	     stop
		    else
        return
		    endif
      end
************************************************************************************
      subroutine tf(lx,ly,node,nodet,obst,temp,nu,xl,yl,sd,dia,t,
     &   time)

c
      
      integer  lx,ly,t,itert,nc,xll,xuu,yll,yuu
      real*8  node(0:8,lx,ly),nodet(0:8,lx,ly),temp(lx,ly),tempo(lx,ly)
      logical  obst(lx,ly)
      integer  x,y,i,j,obsval,iter,time,t0,t1,xu,xl,yu,yl,k,dia
      real*8 u(lx,ly),v(lx,ly),nu,d_loc,pr,alpha,ne(0:8),ot,ti
      real*8 Uc,sd
      real*8 nut,nub,nul,nur,nua(6),f,d,error
      real*8 nuta(6),nuba(6),nula(6),nura(6),nodeteq(0:8,lx,ly)
      real*8 w(0:8), cx(0:8),cy(0:8),tl
      pr=0.71
      ti=1.d0
      tl=0.d0
      !nu=0.02
      alpha=nu/pr
c.....loop over all nodes
        cx(:)=(/0.0,1.0,0.0,-1.0,0.0,1.0,-1.0,-1.0,1.0/)
        cy(:)=(/0.0,0.0,1.0,0.0,-1.0,1.0,1.0,-1.0,-1.0/)
      w(:)=(/4./9.,1./9.,1./9.,1./9.,1./9.,1./36.,1./36.,1./36.,1./36./)
      !open(84,file='temperature.dat')
      ot=2.0/(6.0*alpha+1.0)




      do  y = 1, ly
        do  x = 1, lx

        d_loc = 0.d0
            do  i = 0, 8
              d_loc = d_loc + node(i,x,y)
            enddo

          if (obst(x,y)) then
            u(x,y) = 0.d0
            v(x,y) = 0.d0
c
                else
        !write(*,*)'Called Convective bc x=  ', x, y
            u(x,y) = (node(1,x,y) + node(5,x,y) + node(8,x,y)
     &           -(node(3,x,y) + node(6,x,y) + node(7,x,y))) / d_loc
            v(x,y) = (node(2,x,y) + node(5,x,y) + node(6,x,y)
     &           -(node(4,x,y) + node(7,x,y) + node(8,x,y))) / d_loc
            end if
           if (y.eq.1.and.x.ge.1.and.x.le.lx) then
c       u_x= 0 !(n_hlp(1,x,y+1) + n_hlp(5,x,y+1) + n_hlp(8,x,y+1)
c     &     -(n_hlp(3,x,y+1) + n_hlp(6,x,y+1) + n_hlp(7,x,y+1))) / d_loc
        v(x,y)=0.d0
        endif

        if (y.eq.ly.and.x.ge.1.and.x.le.lx) then
c       u_x=0 !(n_hlp(1,x,y-1) + n_hlp(5,x,y-1) + n_hlp(8,x,y-1)
c     &      -(n_hlp(3,x,y-1) + n_hlp(6,x,y-1) + n_hlp(7,x,y-1))) / d_loc
        v(x,y)=0.d0
        endif

        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


      ! if (x.eq.lx-1) then
		!!!  endif

c
	     !u_curr(y) = u(x,y)
	     !v_curr(y) = v(x,y)

          enddo
          !u_curr(y) = u(x,y)
	 	   !  v_curr(y) = v(x,y)
        enddo

       ! print *,'velocities calculated'

        !!   do y=1,ly
          !     u(x,y)=0.d0
           !     v(x,y)=0.d0
            !    end do
            !end do
!*************************************************************
        u=0.d0
        v=0.d0
        call collt(u,v,nodet,nodeteq,temp,ot,w,cx,cy,lx,ly)
      !  print *,'collision complete'
        ! streaming for scalar
        call streaming(nodet,lx,ly)
       ! call gbound(g,tw,w,lx,ly)
!**************************************************************
    !................boundary conditions

           !top and bottom boundaries periodic
           ! F(m)=F(m-1)

           do  j=1,lx
              !do  i=0,8
              nodet(i,j,1)=nodet(i,j,2)  ! bottom
              nodet(i,j,ly)=nodet(i,j,ly-1)  ! top
              
              !enddo
           enddo


           !inlet boundary condition


           do i=1,ly
           nodet(8,1,i)=(tl+tl)/36.d0-nodet(6,1,i)
           nodet(1,1,i)=(tl+tl)/9.d0-nodet(3,1,i)
           nodet(5,1,i)=(tl+tl)/36.d0-nodet(7,1,i)
           !nodet(0,1,i)=4.d0*ti/9.d0
           enddo

            ! outlet boundary condition
           do j=1,ly
            do i=0,8
                nodet(i,lx,j)=nodet(i,lx-1,j)
           !nodet(6,lx,j)=-nodet(8,lx,j)
           !nodet(3,lx,j)=-nodet(1,lx,j)
           !nodet(7,lx,j)=-nodet(5,lx,j)
            end do
           end do

        ! outlet boundary condition
   !   call convective_BC(lx,ly,obst,nodet,u_curr,u_bdy1,u_prev
    ! &					,v_curr,v_bdy1,v_prev,ot)

        ! constant temperature on the cylinder walls
!...... NOTE THE CODE WORKS PROPERLY ONLY WHEN THIS CONDITION IS IMPOSED PROPERLY
!.......FOR THE OBSTACLE

      do nc=1,6
      xl=7*dia+1
      xu=xl+dia
      yl=9.5*dia+1
      yu=yl+dia-1
      xll=xl+(nc-1)*(sd+1)*dia
      xuu=xll+dia
      yll=yl
      yuu=yll+dia
      ! top wall
      do  i=xll,xuu
        nodet(6,i,yuu)=(ti+ti)/36.d0-nodet(8,i,yuu)
       nodet(2,i,yuu)=(ti+ti)/9.d0-nodet(4,i,yuu)
       nodet(5,i,yuu)=(ti+ti)/36.d0-nodet(7,i,yuu)
       !nodet(0,i,yuu)=4.d0*ti/9.d0
      enddo
      ! bottom wall
      do  i=xll,xuu
        nodet(8,i,yll)=(ti+ti)/36.d0-nodet(6,i,yll)
       nodet(4,i,yll)=(ti+ti)/9.d0-nodet(2,i,yll)
       nodet(7,i,yll)=(ti+ti)/36.d0-nodet(5,i,yll)
       !nodet(1,i,yll)=(ti+ti)/9.d0-nodet(3,i,yll)
      enddo

      ! right wall
      do  i=yll,yuu

       nodet(5,xuu,i)=(ti+ti)/36.d0-nodet(7,xuu,i)
       nodet(1,xuu,i)=(ti+ti)/9.d0-nodet(3,xuu,i)
       nodet(8,xuu,i)=(ti+ti)/36.d0-nodet(6,xuu,i)
       !nodet(0,xuu,i)=4.d0*ti/9.d0
      enddo

      ! left wall
      do  i=yll,yuu

       nodet(6,xll,i)=(ti+ti)/36.d0-nodet(8,xll,i)
       nodet(3,xll,i)=(ti+ti)/9.d0-nodet(1,xll,i)
       nodet(7,xll,i)=(ti+ti)/36.d0-nodet(5,xll,i)
       !nodet(0,xll,i)=4.d0*ti/9.d0
      enddo

      enddo

!********************************************************************
        do  x=1,lx
         do y=1,ly

         temp(x,y)=0.d0
         do  k=0,8
         temp(x,y)=temp(x,y)+nodet(k,x,y)
         enddo
          !write(84,*) x,y,temp(x,y)
      enddo
      enddo

!**************************************************************
		!nusselt is calulated as a non dimensional temperature gradient

        do nc=1,6

          xll=xl+(nc-1)*(sd+1)*dia
          xuu=xll+dia
          yll=yl
          yuu=yll+dia

        nut=0.d0
        nub=0.d0
        nul=0.d0
        nur=0.d0
        ! K is assumed to be one, A=1
       do  i=1,(dia+1)
            nut=nut+((temp(i+xll-1,yuu)-temp(i+xll-1,yuu+1))*float(1))
            nub=nub+((temp(i+xll-1,yll)-temp(i+xll-1,yll-1))*float(1))
            nul=nul+((temp(xll,i+yll-1)-temp(xll-1,i+yll-1))*float(1))
            nur=nur+((temp(xuu,i+yll-1)-temp(xuu+1,i+yll-1))*float(1))
      enddo
          nuta(nc)=nut/float(1)
          nuba(nc)=nub/float(1)
          nula(nc)=nul/float(1)
          nura(nc)=nur/float(1)
          nua(nc)=(nuta(nc)+nuba(nc)+nula(nc)+nura(nc))/4.d0

          enddo

      write(84,*) time,nuta(1),nuba(1),nula(1),nura(1),nua(1),
     &  nuta(2),nuba(2),nula(2),nura(2),nua(2),
     & nuta(3),nuba(3),nula(3),nura(3),nua(3),
     & nuta(4),nuba(4),nula(4),nura(4),nua(4),
     & nuta(5),nuba(5),nula(5),nura(5),nua(5),
     & nuta(6),nuba(6),nula(6),nura(6),nua(6)    
     
        end
!*******************************************************************

        subroutine collt(u,v,g,geq,th,omegat,w,cx,cy,n,m)

        real*8 g(0:8,n,m),geq(0:8,n,m),th(n,m)
        real*8 w(0:8),cx(0:8),cy(0:8)
        real*8 u(n,m),v(n,m),omegat
        print *,'in collision subroutine'
        do i=1,n
        do j=1,m
        do k=0,8
            !print *,'at point =',i,j,k
        geq(k,i,j)=th(i,j)*w(k)*(1.0+3.0*(u(i,j)*cx(k)+v(i,j)*cy(k)))
        g(k,i,j)=omegat*geq(k,i,j)+(1.0-omegat)*g(k,i,j)
        end do
        end do
        end do
        return
        end

        subroutine streaming(f,n,m)
        real*8 f(0:8,n,m)
        ! streaming
        DO j=1,m
        DO i=n,2,-1 !RIGHT TO LEFT
        f(1,i,j)=f(1,i-1,j)
        end do
        DO i=1,n-1 !LEFT TO RIGHT
        f(3,i,j)=f(3,i+1,j)
        END DO
        END DO

        DO j=m,2,-1 !TOP TO BOTTOM
        DO i=1,n
        f(2,i,j)=f(2,i,j-1)
        END DO
        DO i=n,2,-1
        f(5,i,j)=f(5,i-1,j-1)
        END DO
        DO i=1,n-1
        f(6,i,j)=f(6,i+1,j-1)
        END DO
        END DO
        DO j=1,m-1 !BOTTOM TO TOP
        DO i=1,n
        f(4,i,j)=f(4,i,j+1)
        END DO
        DO i=1,n-1
        f(7,i,j)=f(7,i+1,j+1)
        END DO
        DO i=n,2,-1
        f(8,i,j)=f(8,i-1,j+1)
        END DO
        END DO
        return
        end

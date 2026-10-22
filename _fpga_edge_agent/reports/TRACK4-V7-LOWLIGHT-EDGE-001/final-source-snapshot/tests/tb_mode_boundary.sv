`timescale 1ns/1ps
module tb_mode_boundary;
    reg clk=0;always #6.734 clk=~clk;
    reg rst=1,key_n=1,vs=0;
    wire [2:0] mode;
    wire ovs,ohs,ode,fault;
    wire [47:0] rgb;
    v7_fullscreen_mode_control #(.DEBOUNCE_CYCLES(4)) control(
        .clk(clk),.rst(rst),.key_mode_n(key_n),.mode(mode));
    v7_algorithm_video_pair #(.W(40),.H(12),.HTOTAL(100)) video(
        .clk(clk),.rst(rst),.in_vs(vs),.in_hs(1'b0),.in_de(1'b0),.in_rgb(48'd0),
        .cfg_mode(mode),.cfg_threshold(11'd96),.cfg_median_enable(1'b1),
        .out_vs(ovs),.out_hs(ohs),.out_de(ode),.out_rgb(rgb),.sticky_fault(fault));
    task tick(input integer n);repeat(n)begin @(posedge clk);#1;end endtask
    integer timeout;
    initial begin
        tick(4);@(negedge clk);rst=0;tick(14);
        @(negedge clk);key_n=0;
        timeout=0;
        while(!control.mode_press&&timeout<20)begin tick(1);timeout=timeout+1;end
        if(!control.mode_press)$fatal(1,"No qualified press");
        // This VS edge coincides with the controller consuming press.
        @(negedge clk);vs=1;tick(1);
        if(mode!==1||video.frame_mode!==0)$fatal(1,"Same-edge snapshot must retain old mode");
        @(negedge clk);vs=0;tick(2);
        if(video.frame_mode!==0)$fatal(1,"Mode changed inside a frame");
        @(negedge clk);vs=1;tick(1);
        if(video.frame_mode!==1)$fatal(1,"Next frame must adopt pending mode");
        @(negedge clk);rst=1;tick(2);
        if(mode!==0||video.frame_mode!==0||ode)$fatal(1,"Reset state");
        $display("MODE_BOUNDARY_PASS same_edge_old=0 next_frame_new=1 reset_color=0");
        $finish;
    end
endmodule

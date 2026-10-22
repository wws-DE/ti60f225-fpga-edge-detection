`timescale 1ns/1ps
module tb_five_modes;
    parameter W=40,H=12,HT=100,FRAMES=8,FAULT_TEST=0,RESET_TEST=0;
    localparam VT=H+45, FRAME_CYCLES=VT*HT, PAIRS=W*H/2, LATENCY=4*HT+2;
    reg clk=0;always #6.734 clk=~clk;
    reg fast_clk=0;always #3.367 fast_clk=~fast_clk;
    reg rst=1,vs=0,hs=0,de=0;
    reg [47:0] rgb=0;
    wire [2:0] mode;
    reg key_n=1;
    v7_fullscreen_mode_control #(.DEBOUNCE_CYCLES(4)) controls(
        .clk(clk),.rst(rst),.key_mode_n(key_n),.mode(mode));
    reg [10:0] threshold=64;
    reg median_enable=1;
    wire ovs,ohs,ode,fault;
    wire [47:0] orgb;
    v7_algorithm_video_pair #(.W(W),.H(H),.HTOTAL(HT)) dut(
        .clk(clk),.rst(rst),.in_vs(vs),.in_hs(hs),.in_de(de),.in_rgb(rgb),
        .cfg_mode(mode),.cfg_threshold(threshold),.cfg_median_enable(median_enable),
        .out_vs(ovs),.out_hs(ohs),.out_de(ode),.out_rgb(orgb),.sticky_fault(fault));
    reg [47:0] inputs[0:FRAMES*PAIRS-1],golden[0:FRAMES*PAIRS-1];
    // Independent clock-index scoreboard. Includes blanking and first output after reset.
    reg [50:0] expected[0:LATENCY];
    integer n,frame,t,v,h,index,lane,checks=0,outputs=0,rows=0,statuses=0;
    reg [47:0] want_rgb;
    reg [50:0] want;
    integer history=0,slot=0;
    string input_path,golden_path;
    reg check_active=0;
    wire [23:0] serial_rgb;
    wire serial_vs,serial_hs,serial_de;
    actual_serializer serializer(.hdmi_tx_slow_clk(fast_clk),.rgb_vs(ovs),.rgb_hs(ohs),
        .rgb_de(ode),.rgb_datax2(orgb),.actual_rgb(serial_rgb),
        .actual_vs(serial_vs),.actual_hs(serial_hs),.actual_de(serial_de));
    integer serial_lane=0,serial_pixels=0;
    reg [50:0] serial_expect=0;
    reg serial_check=0;
    reg [23:0] serial_want;
    always @(posedge fast_clk)begin
        if(serial_check)begin
            serial_want=serial_expect[serial_lane*24+:24];
            #1;
            if({serial_vs,serial_hs,serial_de}!==serial_expect[50:48])$fatal(1,"Serializer sync");
            if(serial_de)begin
                if(serial_rgb!==serial_want)$fatal(1,"Actual top serializer lane=%0d got=%h want=%h",serial_lane,serial_rgb,serial_want);
                serial_pixels=serial_pixels+1;serial_lane=1-serial_lane;
            end else serial_lane=0;
        end
    end
    always @(posedge clk)begin
        if(!rst&&dut.status_valid)begin
            if(!FAULT_TEST&&dut.status_code!=0)$fatal(1,"Frontend status %0d",dut.status_code);
            if(dut.status_code==0)statuses=statuses+1;
        end
    end
    task step(input reg tvs,ths,tde,input reg[47:0] trgb,texpected);
        begin
            @(negedge clk);vs=tvs;hs=ths;de=tde;rgb=trgb;
            expected[slot]={tvs,ths,tde,texpected};
            @(posedge clk);#1;
            if(history>=LATENCY)begin
                want=expected[(slot+1)%(LATENCY+1)];
                serial_expect=want;serial_check=1;
                if({ovs,ohs,ode}!==want[50:48])
                    $fatal(1,"Sync latency frame=%0d t=%0d history=%0d got=%b expected=%b",frame,t,history,{ovs,ohs,ode},want[50:48]);
                if(ode)begin
                    outputs=outputs+1;
                    if(orgb!==want[47:0])$fatal(1,"Pixel frame=%0d t=%0d output=%0d got=%h expected=%h rowtags=%b disp=(%0d,%0d,f%0d)",frame,t,outputs,orgb,want[47:0],dut.row_complete,dut.display_x,dut.display_y,dut.display_frame);
                end
                checks=checks+1;
            end
            if(!FAULT_TEST&&fault)$fatal(1,"Bridge fault at frame=%0d t=%0d active=%b ready=%b row=%0d inputrow=%0d",frame,t,dut.input_valid,dut.algorithm_ready,dut.display_y,dut.input_y);
            history=history+1;slot=(slot+1)%(LATENCY+1);
        end
    endtask
    initial begin
        if(!$value$plusargs("INPUT=%s",input_path))$fatal(1,"INPUT missing");
        if(!$value$plusargs("GOLD=%s",golden_path))$fatal(1,"GOLD missing");
        $readmemh(input_path,inputs);$readmemh(golden_path,golden);
        repeat(6)@(negedge clk);rst=0;
        if(RESET_TEST)begin
            // Reset in active video after the pipeline and row RAM contain actual data.
            for(t=0;t<35*HT+16;t=t+1)begin
                @(negedge clk);v=t/HT;h=t%HT;
                vs=v<2;hs=h<4;de=v>=30&&h>=10&&h<10+W/2;rgb=48'hf010200010ff;
            end
            @(negedge clk);rst=1;vs=0;hs=0;de=0;rgb=0;
            repeat(6)@(negedge clk);
            if(ode||ovs||ohs||dut.row_complete||fault)$fatal(1,"Reset did not invalidate output/rows");
            rst=0;
        end
        for(frame=0;frame<FRAMES;frame=frame+1)begin
            // Each frame takes the mode selected by the previous frame key press.
            median_enable=1;
            threshold=64;
            for(t=0;t<FRAME_CYCLES;t=t+1)begin
                v=t/HT;h=t%HT;
                // 首帧及复位后的第一帧也必须取64；帧中扰动配置不影响当前帧。
                if(t==3)threshold=511;
                if(t>2&&dut.frame_threshold!==11'd64)$fatal(1,"Frame threshold changed or first frame used reset default");
                // A physical key event inside active video only affects the following frame.
                if(t==(30+H/2)*HT+10)key_n=0;
                if(t==(30+H/2)*HT+22)key_n=1;
                if(t>2&&dut.frame_mode!==(frame%5))$fatal(1,"Frame mode changed mid-frame f=%0d mode=%0d",frame,dut.frame_mode);
                if(FAULT_TEST&&frame==0&&t==30*HT+12)force dut.algorithm_ready=0;
                if(FAULT_TEST&&frame==0&&t==30*HT+13)release dut.algorithm_ready;
                if(v>=30&&v<30+H&&h>=10&&h<10+W/2)begin
                    index=frame*PAIRS+(v-30)*(W/2)+h-10;
                    step(v<2,h<4,1,inputs[index],golden[index]);
                end else step(v<2,h<4,0,48'h0,48'h0);
            end
        end
        for(t=0;t<LATENCY+5;t=t+1)step(0,0,0,0,0);
        if(outputs!=FRAMES*PAIRS)$fatal(1,"Pixel count %0d expected %0d",outputs,FRAMES*PAIRS);
        if(serial_pixels!=FRAMES*W*H)$fatal(1,"Serializer count %0d",serial_pixels);
        if(FAULT_TEST)begin
            if(!fault||statuses!=FRAMES-1)$fatal(1,"Fault/recovery status wrong %b %0d",fault,statuses);
        end else if(statuses!=FRAMES)$fatal(1,"Frame status count %0d expected %0d",statuses,FRAMES);
        $display("FIVE_MODES_PASS W=%0d H=%0d frames=%0d pixels=%0d checked_cycles=%0d latency=%0d statuses=%0d fault_test=%0d reset_test=%0d",W,H,FRAMES,outputs*2,checks,LATENCY,statuses,FAULT_TEST,RESET_TEST);
        $finish;
    end
endmodule

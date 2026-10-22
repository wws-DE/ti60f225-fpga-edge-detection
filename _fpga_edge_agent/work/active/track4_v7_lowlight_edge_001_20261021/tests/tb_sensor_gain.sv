`timescale 1ns/1ps
// 真实初始化器+ROM；wr_done仅模拟控制器完成，不代表实机ACK。
module tb_sensor_gain;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0,init_done=0,wr_done=0;
    wire wr_en,rd_en;
    wire [15:0] addr;
    wire [7:0] data,device;
    reg [24:0] golden[0:163];
    string path;
    integer writes=0,k;
    i2c_master_reg_set #(.DATA_LENGTH(164),.I2C_DEVICE_ADDR(8'h60)) dut(
        .clk(clk),.rst_n(rst_n),.init_done(init_done),.rd_done(1'b0),.wr_done(wr_done),
        .wr_en(wr_en),.rd_en(rd_en),.addr(addr),.dout(data),.dev_addr(device));
    task tick; @(posedge clk); #1; endtask
    task reset_sequence;
        @(negedge clk);rst_n=0;wr_done=0;init_done=0;
        tick();if(wr_en||rd_en)$fatal(1,"Reset enables");
        repeat(3)tick();
        @(negedge clk);rst_n=1;init_done=1;
    endtask
    task transaction(input integer index);
        integer timeout,j;
        reg [23:0] held;
        begin
            timeout=0;
            while(!wr_en&&timeout<30)begin tick();timeout=timeout+1;end
            if(!wr_en||rd_en||device!==8'h60)$fatal(1,"Write request %0d",index);
            if({addr,data,1'b0}!==golden[index])$fatal(1,"ROM index=%0d got=%h expected=%h",index,{addr,data,1'b0},golden[index]);
            writes=writes+1;held={addr,data};
            tick();if(wr_en||rd_en)$fatal(1,"Enable pulse width");
            for(j=0;j<3+index%7;j=j+1)begin
                tick();
                if(wr_en||rd_en||{addr,data}!==held)$fatal(1,"Advanced before completion %0d",index);
            end
            @(negedge clk);wr_done=1;tick();
            @(negedge clk);wr_done=0;
        end
    endtask
    task stopped;
        repeat(20)begin tick();if(wr_en||rd_en)$fatal(1,"Extra transaction after 164");end
    endtask
    initial begin
        if(!$value$plusargs("GOLD=%s",path))$fatal(1,"Missing ROM reference");
        $readmemh(path,golden);
        reset_sequence();for(k=0;k<164;k=k+1)transaction(k);stopped();
        reset_sequence();for(k=0;k<17;k=k+1)transaction(k);
        // 中断一次在途请求，再检查从第0项重新完成全部164项。
        while(!wr_en)tick();
        reset_sequence();for(k=0;k<164;k=k+1)transaction(k);stopped();
        if(writes!=345)$fatal(1,"Write count");
        $display("SENSOR_GAIN_PASS complete_sequences=2 restart_after=17 checked_writes=%0d last_index=163 gain=81/2a mock_completion_only=1",writes);
        $finish;
    end
    initial begin #200000;$fatal(1,"Timeout");end
endmodule

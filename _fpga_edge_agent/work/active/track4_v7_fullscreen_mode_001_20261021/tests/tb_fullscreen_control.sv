`timescale 1ns/1ps
module tb_fullscreen_control;
    parameter integer N=4, PRODUCTION=0;
    reg clk=0;
    always #6.734 clk=~clk;
    reg rst=1, key_n=0;
    wire [2:0] mode;
    v7_fullscreen_mode_control #(.DEBOUNCE_CYCLES(N)) dut(
        .clk(clk),.rst(rst),.key_mode_n(key_n),.mode(mode));
    task tick(input integer n);
        repeat(n) begin @(posedge clk); #1; end
    endtask
    task level(input bit value,input integer n);
        begin @(negedge clk);key_n=value;tick(n);end
    endtask
    task expect_mode(input integer expected);
        if(mode!==expected[2:0])$fatal(1,"Mode got=%0d expected=%0d N=%0d",mode,expected,N);
    endtask
    integer k;
    initial begin
        tick(5);@(negedge clk);rst=0;
        tick(N+8);expect_mode(0); // Startup-held key is not a press.
        level(1,N+8);
        if(PRODUCTION)begin
            level(0,N-1);level(1,N+8);expect_mode(0);
            level(0,N+8);expect_mode(1);
            tick(N+8);expect_mode(1);
            level(1,N+8);level(0,N+8);expect_mode(2);
        end else begin
            repeat(8)begin level(0,1);level(1,1);end
            tick(N+8);expect_mode(0);
            for(k=1;k<=10;k=k+1)begin
                level(0,N+8);expect_mode(k%5);
                tick(3*N+8);expect_mode(k%5);
                level(1,N+8);
            end
            @(negedge clk);force dut.mode_state=3'd5;
            #1;expect_mode(0);
            @(negedge clk);release dut.mode_state;
            tick(2);expect_mode(0);
            @(negedge clk);force dut.mode_state=3'd7;
            #1;expect_mode(0);
            @(negedge clk);release dut.mode_state;
            tick(2);expect_mode(0);
            level(0,N+8);expect_mode(1);
            @(negedge clk);rst=1;tick(3);expect_mode(0);
            @(negedge clk);rst=0;tick(N+8);expect_mode(0);
            level(1,N+8);level(0,N+8);expect_mode(1);
        end
        $display("FULLSCREEN_CONTROL_PASS N=%0d production=%0d",N,PRODUCTION);
        $finish;
    end
endmodule

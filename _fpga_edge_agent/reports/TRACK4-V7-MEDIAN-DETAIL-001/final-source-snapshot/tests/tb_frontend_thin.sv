`timescale 1ns/1ps
module tb_frontend_thin;
 parameter integer W=8,H=5,CONTEXT=1,DIAG=18,COMPARE=0,OWNER=0,THIN=1;
 localparam integer N=W*H/2;
 reg clk=0;always #5 clk=~clk;
 reg rst=1,jv=0,iv=0,ordy=1,cancel=0,srdy=0;
 reg [1:0] kind=1;
 reg [31:0] jobid=0;
 reg [10:0] cfg_t=64,ix=0,iy=0;
 reg [47:0] rgb=0;
 reg sof=0,eol=0,eof=0,bad=0;
 reg estart=0,eflush=0,evalid=0,erdy=1;
 reg [40:0] ein=0;
 wire jr,ir,ov,sv,er,ev,ee;
 wire [15:0] center;
 wire [1:0] edges;
 wire [24:0] coord;
 wire [95:0] ids,sids;
 wire [2:0] scode;
 wire [20:0] count_in,count_out;
 wire [10:0] errx,erry;
 wire [108:0] eout;
 wire bjr,bir,bov,bsv,ber,bev,bee;
 wire [15:0] bcenter;
 wire [1:0] bedges;
 wire [24:0] bcoord;
 wire [95:0] bids,bsids;
 wire [2:0] bscode;
 wire [20:0] bcount_in,bcount_out;
 wire [10:0] berrx,berry;
 wire [108:0] beout;
 reg [47:0] inputs[0:N-1];
 reg [17:0] golden0[0:N-1],golden1[0:N-1];
 reg checking=0;
 integer seen=0,frames=0,statuses=0,stall_count=0,extseen=0;
 reg [31:0] random_state=431;
 string ip,gp0,gp1;
 frontend_frame_pair #(.W(W),.H(H),.SOBEL_COHERENCE_ENABLE(1),.SOBEL_COHERENCE_MIN_DIFF(20),.SOBEL_WEAK_ENABLE(1),.SOBEL_WEAK_MIN_DIFF(18),.SOBEL_WEAK_THRESHOLD_DROP(0),.EDGE_THIN_ENABLE(THIN),.EDGE_THIN_MODE(1),.EDGE_CONTEXT_ENABLE(CONTEXT),.DIAGONAL_ENABLE(CONTEXT),.DIAGONAL_MIN_DIFF(DIAG)) dut(
    .clk(clk),
    .rst(rst),
    .job_valid(jv),
    .job_epoch(32'h13572468),
    .job_frame_id(jobid),
    .job_config_id(jobid+32'd42),
    .job_median_enable(1'b1),
    .job_output_kind(kind),
    .job_threshold(cfg_t),
    .in_valid(iv),
    .in_rgb(rgb),
    .in_x_even(ix),
    .in_y(iy),
    .in_sof(sof),
    .in_eol(eol),
    .in_eof(eof),
    .in_bad(bad),
    .out_ready(ordy),
    .cancel(cancel),
    .external_sobel_owner(1'(OWNER)),
    .external_sobel_start(estart),
    .external_sobel_flush(eflush),
    .external_sobel_open(1'b1),
    .external_sobel_in_valid(evalid),
    .external_sobel_input(ein),
    .external_sobel_out_ready(erdy),
    .status_ready(srdy),
    .job_ready(jr),
    .in_ready(ir),
    .out_valid(ov),
    .out_y_filtered(center),
    .out_edge(edges),
    .out_x_even(coord[10:0]),
    .out_y(coord[21:11]),
    .out_sof(coord[22]),
    .out_eol(coord[23]),
    .out_eof(coord[24]),
    .out_epoch(ids[31:0]),
    .out_frame_id(ids[63:32]),
    .out_config_id(ids[95:64]),
    .external_sobel_in_ready(er),
    .external_sobel_out_valid(ev),
    .external_sobel_output(eout),
    .external_sobel_empty(ee),
    .status_valid(sv),
    .status_code(scode),
    .status_epoch(sids[31:0]),
    .status_frame_id(sids[63:32]),
    .status_config_id(sids[95:64]),
    .status_in_pairs(count_in),
    .status_out_pairs(count_out),
    .status_error_x(errx),
    .status_error_y(erry)
);
frontend_frame_pair_baseline #(.W(W),.H(H),.SOBEL_COHERENCE_ENABLE(1),.SOBEL_COHERENCE_MIN_DIFF(20),.SOBEL_WEAK_ENABLE(1),.SOBEL_WEAK_MIN_DIFF(18),.SOBEL_WEAK_THRESHOLD_DROP(0),.EDGE_CONTEXT_ENABLE(CONTEXT),.DIAGONAL_ENABLE(CONTEXT),.DIAGONAL_MIN_DIFF(DIAG)) baseline(
    .clk(clk),
    .rst(rst),
    .job_valid(jv),
    .job_epoch(32'h13572468),
    .job_frame_id(jobid),
    .job_config_id(jobid+32'd42),
    .job_median_enable(1'b1),
    .job_output_kind(kind),
    .job_threshold(cfg_t),
    .in_valid(iv),
    .in_rgb(rgb),
    .in_x_even(ix),
    .in_y(iy),
    .in_sof(sof),
    .in_eol(eol),
    .in_eof(eof),
    .in_bad(bad),
    .out_ready(ordy),
    .cancel(cancel),
    .external_sobel_owner(1'(OWNER)),
    .external_sobel_start(estart),
    .external_sobel_flush(eflush),
    .external_sobel_open(1'b1),
    .external_sobel_in_valid(evalid),
    .external_sobel_input(ein),
    .external_sobel_out_ready(erdy),
    .status_ready(srdy),
    .job_ready(bjr),
    .in_ready(bir),
    .out_valid(bov),
    .out_y_filtered(bcenter),
    .out_edge(bedges),
    .out_x_even(bcoord[10:0]),
    .out_y(bcoord[21:11]),
    .out_sof(bcoord[22]),
    .out_eol(bcoord[23]),
    .out_eof(bcoord[24]),
    .out_epoch(bids[31:0]),
    .out_frame_id(bids[63:32]),
    .out_config_id(bids[95:64]),
    .external_sobel_in_ready(ber),
    .external_sobel_out_valid(bev),
    .external_sobel_output(beout),
    .external_sobel_empty(bee),
    .status_valid(bsv),
    .status_code(bscode),
    .status_epoch(bsids[31:0]),
    .status_frame_id(bsids[63:32]),
    .status_config_id(bsids[95:64]),
    .status_in_pairs(bcount_in),
    .status_out_pairs(bcount_out),
    .status_error_x(berrx),
    .status_error_y(berry)
);
 always @(posedge clk)begin
   if(!rst)begin
     if(COMPARE)begin
       if({jr,ir,ov,sv,er,ev,ee}!=={bjr,bir,bov,bsv,ber,bev,bee})$fatal(1,"Default compatibility handshake");
       if(ov&&{center,edges,coord,ids}!=={bcenter,bedges,bcoord,bids})$fatal(1,"Default compatibility pixel");
       if(sv&&{scode,sids,count_in,count_out,errx,erry}!=={bscode,bsids,bcount_in,bcount_out,berrx,berry})$fatal(1,"Default compatibility status");
       if(ev&&eout!==beout)$fatal(1,"External owner compatibility data");
     end
     if(ov&&!ordy)stall_count=stall_count+1;
     if(ov&&ordy)begin
       if(ids!=={jobid+32'd42,jobid,32'h13572468})$fatal(1,"Job identity");
       if(checking)begin
         if(seen>=N)$fatal(1,"Extra frontend pixel");
         if({center,edges}!==(kind==0||OWNER?golden0[seen]:golden1[seen]))$fatal(1,"Frontend pixel %0d",seen);
         if(coord!=={seen==N-1,seen%(W/2)==W/2-1,seen==0,11'(seen/(W/2)),11'(2*(seen%(W/2)))})$fatal(1,"Frontend coordinate");
       end
       seen=seen+1;
     end
     if(ev&&erdy&&!estart&&!eflush)extseen=extseen+1;
   end
 end
 task launch(input integer k,input integer normal);
  integer timeout;
  begin
   @(negedge clk);iv=0;bad=0;cancel=0;ordy=1;srdy=0;cfg_t=64;
   timeout=0;while(!jr)begin @(negedge clk);timeout=timeout+1;if(timeout>1000)$fatal(1,"Job not ready");end
   jobid=jobid+1;kind=k;checking=normal;seen=0;jv=1;
   @(posedge clk);if(!jr)$fatal(1,"Job admission");
   @(negedge clk);jv=0;cfg_t=511;
  end
 endtask
 task feed(input integer count,input integer bad_last,input integer stress);
  integer sent,cycles;
  reg blocked;
  begin
   sent=0;cycles=0;blocked=0;
   while(sent<count)begin
    @(negedge clk);random_state=random_state*32'd1664525+32'd1013904223;
    ordy=!stress||random_state[3:0]>3;
    if(stress&&cycles>=18&&cycles<52)ordy=0;
    if(!blocked)iv=!stress||random_state[7:4]>2;
    rgb=inputs[sent];ix=2*(sent%(W/2));iy=sent/(W/2);sof=sent==0;eol=sent%(W/2)==W/2-1;eof=sent==N-1;
    bad=bad_last&&sent==count-1;
    @(posedge clk);blocked=iv&&!ir;if(iv&&ir)sent=sent+1;
    #2;cycles=cycles+1;if(cycles>count*30+1000)$fatal(1,"Input timeout");
   end
   @(negedge clk);iv=0;bad=0;ordy=1;
  end
 endtask
 task status_check(input integer code,input integer expected_inputs);
  integer timeout;
  begin
   timeout=0;while(!sv)begin @(negedge clk);timeout=timeout+1;if(timeout>N*5+200)$fatal(1,"Status timeout");end
   if(scode!==3'(code)||count_in!==21'(expected_inputs))$fatal(1,"Status code/count %0d/%0d",scode,count_in);
   if(sids!=={jobid+32'd42,jobid,32'h13572468})$fatal(1,"Status identity");
   if(checking&&(count_out!=N||seen!=N))$fatal(1,"Full frame count %0d/%0d",count_out,seen);
   if(count_out>count_in)$fatal(1,"Invalid partial count");
   repeat(3)@(negedge clk);
   if(!sv)$fatal(1,"Status not held");
   srdy=1;@(negedge clk);srdy=0;statuses=statuses+1;checking=0;
  end
 endtask
 initial begin
   if(!$value$plusargs("INPUT=%s",ip)||!$value$plusargs("GOLD0=%s",gp0)||!$value$plusargs("GOLD1=%s",gp1))$fatal(1,"Paths missing");
   $readmemh(ip,inputs);$readmemh(gp0,golden0);$readmemh(gp1,golden1);
   repeat(4)@(negedge clk);rst=0;
   launch(0,1);feed(N,0,1);status_check(0,N);frames=frames+1;
   launch(OWNER?0:1,1);feed(N,0,1);status_check(0,N);frames=frames+1;
   launch(OWNER?0:1,0);feed(N/3,0,0);
   @(negedge clk);cancel=1;@(negedge clk);cancel=0;status_check(1,N/3);
   launch(OWNER?0:1,0);feed(N/3,1,0);status_check(2,N/3);
   launch(OWNER?0:1,1);feed(N,0,1);status_check(0,N);frames=frames+1;
   if(OWNER)begin
    @(negedge clk);estart=1;extseen=0;@(negedge clk);estart=0;
    for(integer sent=0;sent<N;)begin
     @(negedge clk);evalid=1;erdy=1;
     ein={sent==N-1,sent%(W/2)==W/2-1,sent==0,11'(sent/(W/2)),11'(2*(sent%(W/2))),16'(sent*17)};
     @(posedge clk);if(evalid&&er)sent=sent+1;#2;
    end
    @(negedge clk);evalid=0;
    for(integer timeout=0;!ee||extseen<N;timeout=timeout+1)begin
     @(negedge clk);if(timeout>N*5+100)$fatal(1,"External drain timeout");end
    if(extseen!=N)$fatal(1,"External count");
    @(negedge clk);eflush=1;@(negedge clk);eflush=0;
   end
   if(statuses!=5)$fatal(1,"Status accounting");
   $display("FRONTEND_THIN_PASS CONTEXT=%0d COMPARE=%0d OWNER=%0d frames=%0d statuses=%0d stalls=%0d external=%0d",CONTEXT,COMPARE,OWNER,frames,statuses,stall_count,extseen);$finish;
 end
endmodule

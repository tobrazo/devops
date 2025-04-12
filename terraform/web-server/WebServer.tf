#---------
# Build web servers
#---------

provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "tobrazo_webserver" {
  count = 2
  ami           = "ami-084568db4383264d4" # Amazon Ubuntu AMI (us-east-1)
  instance_type = "t2.micro"
  vpc_security_group_ids = [aws_security_group.tobrazo_webserver.id]
  user_data = templatefile("${path.module}/userdata.tpl", {
    instance_name = "server${count.index + 1}"
  })
  availability_zone = element(["us-east-1a", "us-east-1b"], count.index)

  tags = {
    Name = "TerraformWebServer"
  }

}

output "webserver_ip" {
  value = aws_instance.tobrazo_webserver[*].public_ip
}

resource "aws_elb" "tobrazo_elb" {
  name               = "tobrazo-classic-elb"
  availability_zones = ["us-east-1a", "us-east-1b"]

  listener {
    instance_port     = 80
    instance_protocol = "http"
    lb_port           = 80
    lb_protocol       = "http"
  }

  health_check {
    target              = "HTTP:80/"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  instances                   = aws_instance.tobrazo_webserver[*].id
  cross_zone_load_balancing  = true
  idle_timeout               = 400
  connection_draining        = true
  connection_draining_timeout = 400

  tags = {
    Name = "tobrazo-classic-elb"
  }
}

output "elb_dns_name" {
  value = aws_elb.tobrazo_elb.dns_name
}

resource "aws_security_group" "tobrazo_webserver" {
  name = "webserver dynamic security group"

  dynamic "ingress" {
    for_each = ["80", "443"]
    content {
      from_port = ingress.value
      to_port = ingress.value
      protocol = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }


  ingress {
    from_port = 22
    to_port   = 22
    protocol = "tcp"
    cidr_blocks = ["10.10.10.10/32"]
  }

  egress {
    from_port = 0
    to_port   = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}